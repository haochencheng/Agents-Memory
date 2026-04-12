from __future__ import annotations

import os
import shutil
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from agents_memory.constants import (
    CATEGORIES,
    DEFAULT_OLLAMA_HOST,
    DOMAINS,
    EMBED_MODEL,
    EMBED_PROVIDER_ENV,
    OLLAMA_EMBED_DIM,
    OLLAMA_EMBED_MODEL,
    OLLAMA_HOST_ENV,
    PROJECTS,
    VECTOR_THRESHOLD,
)
from agents_memory.logging_utils import log_file_update
from agents_memory.runtime import AppContext
from agents_memory.services.workflow_records import is_error_record_meta, normalize_project_id


def parse_frontmatter(filepath: Path) -> dict:
    # Parse YAML frontmatter key-value pairs between the first two --- delimiters.
    meta: dict = {}
    in_front = False
    for line in filepath.read_text(encoding="utf-8").splitlines():
        line = line.rstrip()
        if line == "---":
            if not in_front:
                in_front = True
                continue
            break
        if in_front and ": " in line:
            key, value = line.split(": ", 1)
            meta[key.strip()] = value.strip().strip('"')
    return meta


def read_body(filepath: Path) -> str:
    lines = filepath.read_text(encoding="utf-8").splitlines()
    body_lines: list[str] = []
    fence_count = 0
    for line in lines:
        if line.strip() == "---":
            fence_count += 1
            continue
        if fence_count >= 2:
            body_lines.append(line)
    return "\n".join(body_lines)


def collect_errors(ctx: AppContext, status_filter: list[str] | None = None) -> list[dict]:
    records = []
    for filepath in sorted(ctx.errors_dir.glob("*.md")):
        meta = parse_frontmatter(filepath)
        if not meta:
            continue
        if not is_error_record_meta(meta):
            continue
        if status_filter and meta.get("status") not in status_filter:
            continue
        normalized_project = normalize_project_id(meta.get("project", ""))
        if normalized_project:
            meta["project"] = normalized_project
        meta["_file"] = str(filepath)
        records.append(meta)
    return records


def total_error_count(ctx: AppContext) -> int:
    return len(list(ctx.errors_dir.glob("*.md")))


def cmd_list(ctx: AppContext) -> None:
    records = collect_errors(ctx, status_filter=["new", "reviewed"])
    if not records:
        print("No active error records found.")
        return
    print(f"\n{'ID':<38} {'Project':<20} {'Category':<18} {'Sev':<10} Status")
    print("-" * 98)
    for record in records:
        print(
            f"{record.get('id', ''):<38} {record.get('project', ''):<20} "
            f"{record.get('category', ''):<18} {record.get('severity', ''):<10} {record.get('status', '')}"
        )
    print(f"\nTotal: {len(records)} active records")


def _gather_record_stats(records: list[dict]) -> tuple[Counter, Counter, Counter]:
    # Count error records grouped by category, project, and status.
    categories = Counter(r.get("category", "unknown") for r in records)
    projects = Counter(r.get("project", "unknown") for r in records)
    statuses = Counter(r.get("status", "unknown") for r in records)
    return categories, projects, statuses


def cmd_stats(ctx: AppContext) -> None:
    # Print summary statistics for error records grouped by category, project, and status.
    records = collect_errors(ctx)
    if not records:
        print("No records found.")
        return
    categories, projects, statuses = _gather_record_stats(records)

    print("\n=== By Category ===")
    for category, count in categories.most_common():
        print(f"  {category:<22} {count}")
    print("\n=== By Project ===")
    for project, count in projects.most_common():
        print(f"  {project:<22} {count}")
    print("\n=== By Status ===")
    for status, count in statuses.most_common():
        print(f"  {status:<22} {count}")

    count = total_error_count(ctx)
    print(f"\nTotal records: {count}")
    if count >= VECTOR_THRESHOLD:
        print(f"\n⚡ 记录数已超过 {VECTOR_THRESHOLD}，建议切换到向量搜索：")
        print("   python3 scripts/memory.py embed")
        print("   python3 scripts/memory.py vsearch <query>")


def cmd_search(ctx: AppContext, keyword: str) -> None:
    # Search error record files for a keyword and print matching record metadata.
    lowered = keyword.lower()
    matches: list[tuple[str, dict]] = []
    for filepath in sorted(ctx.errors_dir.glob("*.md")):
        content = filepath.read_text(encoding="utf-8").lower()
        if lowered in content:
            matches.append((filepath.name, parse_frontmatter(filepath)))
    if not matches:
        print(f"No records matching '{keyword}'")
        return

    print(f"\nFound {len(matches)} match(es) for '{keyword}':\n")
    for filename, meta in matches:
        print(f"  {filename}")
        print(f"    project={meta.get('project', '')}  category={meta.get('category', '')}  status={meta.get('status', '')}")


def cmd_promote(ctx: AppContext, record_id: str) -> None:
    matched: Path | None = None
    for filepath in ctx.errors_dir.glob("*.md"):
        meta = parse_frontmatter(filepath)
        if meta.get("id") == record_id:
            matched = filepath
            break
    if matched is None:
        print(f"Record '{record_id}' not found.")
        return

    instruction_path = input(
        "Write instruction file path (e.g., .github/instructions/python.instructions.md): "
    ).strip()
    content = matched.read_text(encoding="utf-8")
    content = content.replace("status: reviewed", "status: promoted")
    content = content.replace('promoted_to: ""', f'promoted_to: "{instruction_path}"')
    matched.write_text(content, encoding="utf-8")
    print(f"Promoted {record_id} → {instruction_path}")
    cmd_update_index(ctx)


def cmd_archive(ctx: AppContext) -> None:
    # Move reviewed/promoted records older than 90 days to the archive directory.
    cutoff = date.today() - timedelta(days=90)
    ctx.archive_dir.mkdir(parents=True, exist_ok=True)
    archived = 0
    for filepath in ctx.errors_dir.glob("*.md"):
        meta = parse_frontmatter(filepath)
        if meta.get("status") not in ("reviewed", "promoted"):
            continue
        try:
            record_date = date.fromisoformat(meta.get("date", ""))
        except ValueError:
            continue
        if record_date < cutoff and int(meta.get("repeat_count", "1")) <= 1:
            target = ctx.archive_dir / filepath.name
            shutil.move(str(filepath), str(target))
            archived += 1
            log_file_update(ctx.logger, action="archive", path=target, detail=f"source={filepath.name}")
            print(f"  Archived: {filepath.name}")
    print(f"\n{archived} record(s) archived.")
    if archived:
        cmd_update_index(ctx)


def _build_categories_str(active: list) -> str:
    categories = Counter(record.get("category", "") for record in active)
    return (
        "\n".join(f"| `{cat}` | {count} |" for cat, count in categories.most_common(3))
        or "| _暂无_ | - |"
    )


def _build_recent_rules_str(promoted: list) -> str:
    recent = sorted(promoted, key=lambda r: r.get("date", ""), reverse=True)[:3]
    return (
        "\n".join(f"- **{r.get('id', '')}**: {r.get('promoted_to', '')}" for r in recent)
        or "_暂无_"
    )


def _build_index_content(total: int, len_promoted: int, top3_str: str, rules_str: str, vector_hint: str, search_cmd: str) -> str:
    return f"""# Agent Memory Index — Hot Tier

> 这是 Agent 每次启动时**必须加载**的唯一文件，严格控制在 400 tokens 以内。
> 其余所有内容通过 semantic search 或按需读取。
{vector_hint}
## 当前活跃规则总数

| 类别 | 数量 | 文件 |
|------|------|------|
| 错误模式 (errors) | {total} | `errors/` |
| 升级规则 (promoted) | {len_promoted} | `memory/rules.md` |

## 最近升级的规则（Top 3）

{rules_str}

## 最高频错误类别（Top 3）

| Category | Count |
|----------|-------|
{top3_str}

## 检索指引

- 写代码前：查 `memory/rules.md` 匹配项目领域规则
- 代码出错后：`python3 scripts/memory.py {search_cmd} <keyword>`
- 写 Finance 代码：额外加载 `memory/rules.md`（Finance 段）
- 做文档变更：检查 docs-drift 类别的错误记录

## 快速提交新错误

```
errors/YYYY-MM-DD-<project>-<sequence>.md
```

格式见 `schema/error-record.md`
"""


def cmd_update_index(ctx: AppContext) -> None:
    # Update the hot-tier index file with current error statistics.
    active = collect_errors(ctx, status_filter=["new", "reviewed"])
    promoted = collect_errors(ctx, status_filter=["promoted"])
    total = total_error_count(ctx)
    vector_hint = ""
    if total >= VECTOR_THRESHOLD:
        vector_hint = (
            f"\n> ⚡ 记录数 ({total}) 已超过 {VECTOR_THRESHOLD}，"
            f"已启用向量语义搜索。运行 `python3 scripts/memory.py embed` 更新索引。\n"
        )
    content = _build_index_content(
        total=total,
        len_promoted=len(promoted),
        top3_str=_build_categories_str(active),
        rules_str=_build_recent_rules_str(promoted),
        vector_hint=vector_hint,
        search_cmd="vsearch" if total >= VECTOR_THRESHOLD else "search ",
    )
    ctx.index_file.write_text(content, encoding="utf-8")
    log_file_update(ctx.logger, action="write", path=ctx.index_file, detail=f"total_records={total}")
    print("index.md updated.")


def _build_new_record_id(ctx: AppContext, project: str, today: str) -> tuple[str, Path]:
    existing = list(ctx.errors_dir.glob(f"{today}-{project}-*.md"))
    seq = str(len(existing) + 1).zfill(3)
    record_id = f"{today}-{project}-{seq}"
    return record_id, ctx.errors_dir / f"{record_id}.md"


def _prompt_record_fields() -> dict:
    # Gather descriptive fields for a new error record interactively.
    print(f"\nCategories: {', '.join(CATEGORIES)}")
    category = input("Category: ").strip() or "runtime-error"
    print(f"\nDomains: {', '.join(DOMAINS)}")
    domain = input("Domain: ").strip() or "other"
    severity = input("Severity (critical/warning/info) [warning]: ").strip() or "warning"
    task = input("What were you trying to do? (1 line): ").strip()
    error_desc = input("What went wrong? (1 line): ").strip()
    root_cause = input("Why did it happen? (1 line): ").strip()
    fix = input("How was it fixed? (1 line): ").strip()
    rule = input("Prevention rule (1-2 sentences): ").strip()
    return {"category": category, "domain": domain, "severity": severity,
            "task": task, "error_desc": error_desc, "root_cause": root_cause,
            "fix": fix, "rule": rule}


def _build_new_record_content(record_id: str, today: str, *, project: str, domain: str,
                              category: str, severity: str, task: str, error_desc: str,
                              root_cause: str, fix: str, rule: str) -> str:
    return f"""---
id: {record_id}
date: {today}
project: {project}
domain: {domain}
category: {category}
severity: {severity}
status: new
promoted_to: ""
repeat_count: 1
tags: []
---

## 错误上下文

**任务目标：**
{task}

**出错文件 / 位置：**
<!-- 填写文件路径 -->

## 错误描述

{error_desc}

## 根因分析

{root_cause}

## 修复方案

{fix}

## 提炼规则

{rule}

## 关联

<!-- 关联记录 ID 或 instruction 文件 -->
"""


def cmd_new(ctx: AppContext) -> None:
    # Interactively prompt for a new error record and write it to disk.
    print("\n=== New Error Record ===\n")
    today = date.today().isoformat()
    print(f"Projects: {', '.join(PROJECTS)}")
    project = input("Project: ").strip() or "other"
    record_id, filepath = _build_new_record_id(ctx, project, today)
    fields = _prompt_record_fields()
    content = _build_new_record_content(record_id, today, project=project, **fields)
    ctx.errors_dir.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")
    print(f"\nCreated: {filepath}")
    cmd_update_index(ctx)


def build_record_text(meta: dict, filepath: Path) -> str:
    header = " ".join(filter(None, [
        meta.get("category", ""),
        meta.get("project", ""),
        meta.get("domain", ""),
        meta.get("severity", ""),
    ]))
    body = read_body(filepath)
    return f"{header}\n{body}"[:3000]


def _get_openai_embedding(text: str) -> list[float]:
    try:
        import openai
    except ImportError:
        print("请先安装 openai: pip install openai")
        sys.exit(1)
    client = openai.OpenAI()
    response = client.embeddings.create(model=EMBED_MODEL, input=text)
    return response.data[0].embedding


def _get_ollama_embedding(text: str) -> list[float]:
    """Call Ollama /api/embeddings endpoint with nomic-embed-text.

    Requires Ollama running locally (default http://localhost:11434).
    Pull the model first:  ollama pull nomic-embed-text
    """
    import json as _json
    import urllib.request
    host = os.environ.get(OLLAMA_HOST_ENV, DEFAULT_OLLAMA_HOST).rstrip("/")
    url = f"{host}/api/embeddings"
    payload = _json.dumps({"model": OLLAMA_EMBED_MODEL, "prompt": text}).encode()
    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            data = _json.loads(resp.read())
        return data["embedding"]
    except Exception as exc:  # noqa: BLE001
        print(f"Ollama embedding 调用失败 ({url}): {exc}")
        print("请确认 Ollama 已启动且已拉取模型: ollama pull nomic-embed-text")
        sys.exit(1)


def get_embedding(text: str) -> list[float]:
    """Return an embedding vector for *text*.

    Provider is selected by AMEM_EMBED_PROVIDER env var:
      - 'openai'  (default): OpenAI text-embedding-3-small (1536d, requires OPENAI_API_KEY)
      - 'ollama':            Ollama nomic-embed-text (768d, local, free)
    """
    provider = os.environ.get(EMBED_PROVIDER_ENV, "openai")
    if provider == "ollama":
        return _get_ollama_embedding(text)
    return _get_openai_embedding(text)
