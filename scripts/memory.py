#!/usr/bin/env python3
"""
Agents-Memory CLI — 错误记录管理工具

用法:
  python3 memory.py new                        # 交互式创建新错误记录
  python3 memory.py list                       # 列出所有 new/reviewed 状态的记录
  python3 memory.py stats                      # 统计各类别错误数量
  python3 memory.py search <keyword>           # 关键词搜索（< 200 条默认策略）
  python3 memory.py vsearch <query>            # 语义向量搜索（需先运行 embed）
  python3 memory.py embed                      # 构建 / 更新本地 LanceDB 向量索引
  python3 memory.py promote <id>               # 将错误记录升级为 instruction 规则
  python3 memory.py sync                       # 将已升级规则自动写入注册项目的 instruction 文件
  python3 memory.py bridge-install <project>   # 在注册项目中安装 bridge instruction
  python3 memory.py register [path]            # 一键注册新项目（自动检测 + 安装 bridge + 写入 mcp.json）
  python3 memory.py mcp-setup [project-id]     # 在已注册项目中写入 .vscode/mcp.json
  python3 memory.py archive                    # 归档 90 天以上且无重复的记录
  python3 memory.py update-index               # 重新生成 index.md 统计数字
  python3 memory.py to-qdrant                  # 迁移向量索引到 Qdrant（多 Agent 共享）

依赖安装:
  基础（关键词搜索）: 无需额外依赖，纯标准库
  向量搜索（本地）:   pip install lancedb openai pyarrow
  Qdrant 迁移:       pip install qdrant-client
"""

import os
import re
import sys
import shutil
from datetime import date, timedelta
from pathlib import Path

# ─── 路径常量 ────────────────────────────────────────────────────────────────
# AGENTS_MEMORY_ROOT 可通过环境变量覆盖，供全局安装的 `amem` CLI 使用

BASE_DIR      = Path(os.environ.get("AGENTS_MEMORY_ROOT", Path(__file__).parent.parent))
ERRORS_DIR    = BASE_DIR / "errors"
ARCHIVE_DIR   = BASE_DIR / "errors" / "archive"
MEMORY_DIR    = BASE_DIR / "memory"
VECTOR_DIR    = BASE_DIR / "vectors"          # LanceDB 本地文件目录（gitignored）
INDEX_FILE    = BASE_DIR / "index.md"
PROJECTS_FILE = MEMORY_DIR / "projects.md"   # 注册项目注册表
TEMPLATES_DIR = BASE_DIR / "templates"       # bridge instruction 模板

# 超过此数量自动推荐向量搜索
VECTOR_THRESHOLD = 200

# OpenAI embedding 模型（1536 维）
EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM   = 1536

# Qdrant 连接（docker-compose 默认）
QDRANT_HOST       = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT       = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "agents-memory")

# ─── 枚举常量 ────────────────────────────────────────────────────────────────

CATEGORIES = [
    "type-error", "logic-error", "finance-safety", "arch-violation",
    "test-failure", "docs-drift", "config-error", "build-error",
    "runtime-error", "security",
]

PROJECTS = [
    "synapse-network", "spec2flow", "provider-service",
    "gateway", "admin-front", "gateway-admin", "other",
]

DOMAINS = ["finance", "frontend", "python", "docs", "config", "infra", "other"]



# ─── 公共工具 ────────────────────────────────────────────────────────────────

def parse_frontmatter(filepath: Path) -> dict:
    """解析 Markdown 文件头部 YAML frontmatter（仅支持 key: value 格式）。"""
    meta: dict = {}
    in_front = False
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip()
            if line == "---":
                if not in_front:
                    in_front = True
                    continue
                else:
                    break
            if in_front and ": " in line:
                key, _, value = line.partition(": ")
                meta[key.strip()] = value.strip().strip('"')
    return meta


def read_body(filepath: Path) -> str:
    """读取 Markdown 正文（frontmatter 之后的内容）。"""
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


def collect_errors(status_filter: list[str] | None = None) -> list[dict]:
    records = []
    for filepath in sorted(ERRORS_DIR.glob("*.md")):
        meta = parse_frontmatter(filepath)
        if not meta:
            continue
        if status_filter and meta.get("status") not in status_filter:
            continue
        meta["_file"] = str(filepath)
        records.append(meta)
    return records


def total_error_count() -> int:
    return len(list(ERRORS_DIR.glob("*.md")))


# ─── 基础命令 ────────────────────────────────────────────────────────────────

def cmd_list():
    records = collect_errors(status_filter=["new", "reviewed"])
    if not records:
        print("No active error records found.")
        return
    print(f"\n{'ID':<38} {'Project':<20} {'Category':<18} {'Sev':<10} Status")
    print("-" * 98)
    for r in records:
        print(
            f"{r.get('id',''):<38} {r.get('project',''):<20} "
            f"{r.get('category',''):<18} {r.get('severity',''):<10} {r.get('status','')}"
        )
    print(f"\nTotal: {len(records)} active records")


def cmd_stats():
    records = collect_errors()
    if not records:
        print("No records found.")
        return
    from collections import Counter
    cats     = Counter(r.get("category", "unknown") for r in records)
    projs    = Counter(r.get("project",  "unknown") for r in records)
    statuses = Counter(r.get("status",   "unknown") for r in records)
    print("\n=== By Category ===")
    for cat, count in cats.most_common():
        print(f"  {cat:<22} {count}")
    print("\n=== By Project ===")
    for proj, count in projs.most_common():
        print(f"  {proj:<22} {count}")
    print("\n=== By Status ===")
    for status, count in statuses.most_common():
        print(f"  {status:<22} {count}")
    count = total_error_count()
    print(f"\nTotal records: {count}")
    if count >= VECTOR_THRESHOLD:
        print(f"\n⚡ 记录数已超过 {VECTOR_THRESHOLD}，建议切换到向量搜索：")
        print("   python3 scripts/memory.py embed")
        print("   python3 scripts/memory.py vsearch <query>")


def cmd_search(keyword: str):
    """关键词全文搜索（< 200 条的默认策略）。"""
    keyword = keyword.lower()
    matches = []
    for filepath in sorted(ERRORS_DIR.glob("*.md")):
        content = filepath.read_text(encoding="utf-8").lower()
        if keyword in content:
            meta = parse_frontmatter(filepath)
            matches.append((filepath.name, meta))
    if not matches:
        print(f"No records matching '{keyword}'")
        return
    print(f"\nFound {len(matches)} match(es) for '{keyword}':\n")
    for fname, meta in matches:
        print(f"  {fname}")
        print(f"    project={meta.get('project','')}  category={meta.get('category','')}  status={meta.get('status','')}")


def cmd_promote(record_id: str):
    matched = None
    for filepath in ERRORS_DIR.glob("*.md"):
        meta = parse_frontmatter(filepath)
        if meta.get("id") == record_id:
            matched = filepath
            break
    if not matched:
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
    cmd_update_index()


def cmd_archive():
    cutoff = date.today() - timedelta(days=90)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archived = 0
    for filepath in list(ERRORS_DIR.glob("*.md")):
        meta = parse_frontmatter(filepath)
        if meta.get("status") not in ("reviewed", "promoted"):
            continue
        try:
            record_date = date.fromisoformat(meta.get("date", ""))
        except ValueError:
            continue
        if record_date < cutoff and int(meta.get("repeat_count", "1")) <= 1:
            shutil.move(str(filepath), str(ARCHIVE_DIR / filepath.name))
            archived += 1
            print(f"  Archived: {filepath.name}")
    print(f"\n{archived} record(s) archived.")
    if archived:
        cmd_update_index()


def cmd_update_index():
    active   = collect_errors(status_filter=["new", "reviewed"])
    promoted = collect_errors(status_filter=["promoted"])
    total    = total_error_count()

    from collections import Counter
    cats      = Counter(r.get("category", "") for r in active)
    top3_cats = cats.most_common(3)
    recent_promoted = sorted(promoted, key=lambda r: r.get("date", ""), reverse=True)[:3]

    top3_cats_str = "\n".join(
        f"| `{cat}` | {count} |" for cat, count in top3_cats
    ) or "| _暂无_ | - |"

    recent_rules_str = "\n".join(
        f"- **{r.get('id','')}**: {r.get('promoted_to','')}"
        for r in recent_promoted
    ) or "_暂无_"

    vector_hint = ""
    if total >= VECTOR_THRESHOLD:
        vector_hint = (
            f"\n> ⚡ 记录数 ({total}) 已超过 {VECTOR_THRESHOLD}，"
            f"已启用向量语义搜索。运行 `python3 scripts/memory.py embed` 更新索引。\n"
        )

    search_cmd = "vsearch" if total >= VECTOR_THRESHOLD else "search "

    index_content = f"""# Agent Memory Index — Hot Tier

> 这是 Agent 每次启动时**必须加载**的唯一文件，严格控制在 400 tokens 以内。
> 其余所有内容通过 semantic search 或按需读取。
{vector_hint}
## 当前活跃规则总数

| 类别 | 数量 | 文件 |
|------|------|------|
| 错误模式 (errors) | {total} | `errors/` |
| 升级规则 (promoted) | {len(promoted)} | `memory/rules.md` |

## 最近升级的规则（Top 3）

{recent_rules_str}

## 最高频错误类别（Top 3）

| Category | Count |
|----------|-------|
{top3_cats_str}

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
    INDEX_FILE.write_text(index_content, encoding="utf-8")
    print("index.md updated.")


def cmd_new():
    print("\n=== New Error Record ===\n")
    today = date.today().isoformat()
    print(f"Projects: {', '.join(PROJECTS)}")
    project = input("Project: ").strip() or "other"
    existing = list(ERRORS_DIR.glob(f"{today}-{project}-*.md"))
    seq = str(len(existing) + 1).zfill(3)
    record_id = f"{today}-{project}-{seq}"
    filename = ERRORS_DIR / f"{record_id}.md"
    print(f"\nCategories: {', '.join(CATEGORIES)}")
    category = input("Category: ").strip() or "runtime-error"
    print(f"\nDomains: {', '.join(DOMAINS)}")
    domain   = input("Domain: ").strip() or "other"
    severity = input("Severity (critical/warning/info) [warning]: ").strip() or "warning"
    task       = input("What were you trying to do? (1 line): ").strip()
    error_desc = input("What went wrong? (1 line): ").strip()
    root_cause = input("Why did it happen? (1 line): ").strip()
    fix        = input("How was it fixed? (1 line): ").strip()
    rule       = input("Prevention rule (1-2 sentences): ").strip()
    content = f"""---
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
    ERRORS_DIR.mkdir(parents=True, exist_ok=True)
    filename.write_text(content, encoding="utf-8")
    print(f"\nCreated: {filename}")
    cmd_update_index()


# ─── 向量搜索 — LanceDB（本地，无服务端）──────────────────────────────────────

def _build_record_text(meta: dict, filepath: Path) -> str:
    """把 frontmatter + 正文拼成 embedding 用的文本，截断到 3000 字符。"""
    header = " ".join(filter(None, [
        meta.get("category", ""),
        meta.get("project", ""),
        meta.get("domain", ""),
        meta.get("severity", ""),
    ]))
    body = read_body(filepath)
    return f"{header}\n{body}"[:3000]


def get_embedding(text: str) -> list[float]:
    """调用 OpenAI text-embedding-3-small。需要 OPENAI_API_KEY 环境变量。"""
    try:
        import openai
    except ImportError:
        print("请先安装 openai: pip install openai")
        sys.exit(1)
    client = openai.OpenAI()
    response = client.embeddings.create(model=EMBED_MODEL, input=text)
    return response.data[0].embedding


def cmd_embed():
    """构建 / 更新本地 LanceDB 向量索引。需要：pip install lancedb openai pyarrow"""
    try:
        import lancedb
    except ImportError:
        print("请先安装依赖：pip install lancedb openai pyarrow")
        sys.exit(1)

    all_files = sorted(ERRORS_DIR.glob("*.md"))
    if ARCHIVE_DIR.exists():
        all_files += sorted(ARCHIVE_DIR.glob("*.md"))

    if not all_files:
        print("No error records to embed.")
        return

    records_raw = [(parse_frontmatter(f), f) for f in all_files if parse_frontmatter(f)]
    print(f"Embedding {len(records_raw)} records using {EMBED_MODEL}...")

    VECTOR_DIR.mkdir(parents=True, exist_ok=True)
    db = lancedb.connect(str(VECTOR_DIR))

    rows = []
    for i, (meta, filepath) in enumerate(records_raw, 1):
        text   = _build_record_text(meta, filepath)
        vector = get_embedding(text)
        rows.append({
            "id":       meta.get("id", filepath.stem),
            "project":  meta.get("project", ""),
            "category": meta.get("category", ""),
            "domain":   meta.get("domain", ""),
            "severity": meta.get("severity", ""),
            "status":   meta.get("status", ""),
            "filepath": str(filepath),
            "text":     text,
            "vector":   vector,
        })
        print(f"  [{i}/{len(records_raw)}] {meta.get('id', filepath.stem)}")

    # 全量重建
    if "errors" in db.table_names():
        db.drop_table("errors")
    db.create_table("errors", data=rows)
    print(f"\nVector index built: {len(rows)} records → {VECTOR_DIR}/errors.lance")
    cmd_update_index()


def cmd_vsearch(query: str, top_k: int = 5):
    """
    语义向量搜索。
    - 若 LanceDB 不可用或索引未建立，自动回退到关键词搜索。
    - 记录数 < VECTOR_THRESHOLD 时提示使用 search 命令。
    """
    try:
        import lancedb
    except ImportError:
        print("LanceDB 未安装，回退到关键词搜索。安装：pip install lancedb openai pyarrow")
        cmd_search(query)
        return

    if not VECTOR_DIR.exists():
        print("向量索引不存在。请先运行：python3 scripts/memory.py embed")
        print("回退到关键词搜索...\n")
        cmd_search(query)
        return

    db = lancedb.connect(str(VECTOR_DIR))
    if "errors" not in db.table_names():
        print("向量表为空。请先运行：python3 scripts/memory.py embed")
        cmd_search(query)
        return

    count = total_error_count()
    if count < VECTOR_THRESHOLD:
        print(f"当前记录数 ({count}) 未达向量搜索阈值 ({VECTOR_THRESHOLD})，使用关键词搜索。\n")
        cmd_search(query)
        return

    print(f"Semantic search: '{query}'  (top {top_k})\n")
    query_vector = get_embedding(query)
    results = db.open_table("errors").search(query_vector).limit(top_k).to_list()

    if not results:
        print(f"No semantic matches for '{query}'")
        return

    print(f"{'Score':<10} {'ID':<38} {'Project':<20} {'Category':<18} Status")
    print("-" * 100)
    for r in results:
        dist = r.get("_distance", 0.0)
        sim  = max(0.0, 1.0 - dist)
        print(
            f"{sim:<10.4f} {r['id']:<38} {r['project']:<20} "
            f"{r['category']:<18} {r['status']}"
        )


# ─── Qdrant 迁移（多 Agent 共享记忆）─────────────────────────────────────────

def cmd_to_qdrant():
    """
    把本地 LanceDB 向量索引迁移到 Qdrant。
    前提：
      1. 已运行 `python3 scripts/memory.py embed`
      2. Qdrant 已通过 docker/docker-compose.yml 启动
      3. pip install qdrant-client
    """
    try:
        import lancedb
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams, PointStruct
    except ImportError:
        print("请先安装：pip install qdrant-client lancedb")
        sys.exit(1)

    if not VECTOR_DIR.exists():
        print("本地 LanceDB 索引不存在。请先运行：python3 scripts/memory.py embed")
        sys.exit(1)

    db = lancedb.connect(str(VECTOR_DIR))
    if "errors" not in db.table_names():
        print("LanceDB 向量表为空，请先运行 embed。")
        sys.exit(1)

    rows = db.open_table("errors").to_list()
    if not rows:
        print("向量表中没有数据。")
        return

    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    existing = [c.name for c in client.get_collections().collections]
    if QDRANT_COLLECTION in existing:
        print(f"集合 '{QDRANT_COLLECTION}' 已存在，删除并重建...")
        client.delete_collection(QDRANT_COLLECTION)

    client.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
    )

    points = [
        PointStruct(
            id=i,
            vector=row["vector"],
            payload={k: row[k] for k in ("id", "project", "category", "domain", "severity", "status", "filepath")},
        )
        for i, row in enumerate(rows)
    ]

    client.upsert(collection_name=QDRANT_COLLECTION, points=points)
    print(f"✅ 迁移完成：{len(points)} 条记录 → Qdrant ({QDRANT_HOST}:{QDRANT_PORT}/{QDRANT_COLLECTION})")
    print(f"\nQdrant Dashboard: http://{QDRANT_HOST}:6333/dashboard")


# ─── 跨项目同步 ──────────────────────────────────────────────────────────────

def _parse_projects() -> list[dict]:
    """解析 memory/projects.md，返回已注册的活跃项目列表。"""
    if not PROJECTS_FILE.exists():
        return []
    projects: list[dict] = []
    current: dict = {}
    for line in PROJECTS_FILE.read_text(encoding="utf-8").splitlines():
        m_header = re.match(r'^## (.+)', line)
        if m_header:
            pid = m_header.group(1).strip()
            if current.get("id"):
                projects.append(current)
            # Skip comment headers (Chinese text sections)
            if any(c > '\u4e00' for c in pid):
                current = {}
            else:
                current = {"id": pid}
            continue
        if not current:
            continue
        m_field = re.match(r'\s*-\s+\*\*(\w+)\*\*:\s*(.*)', line)
        if m_field:
            key, val = m_field.group(1).strip(), m_field.group(2).strip()
            current[key] = val
    if current.get("id"):
        projects.append(current)
    return [p for p in projects if p.get("active", "true").lower() == "true"]


def _extract_rule_text(filepath: Path) -> str:
    """从错误记录文件提取 '提炼规则' 段落的纯文本。"""
    lines = filepath.read_text(encoding="utf-8").splitlines()
    in_rule = False
    rule_lines: list[str] = []
    for line in lines:
        if line.strip() == "## 提炼规则":
            in_rule = True
            continue
        if in_rule:
            if line.startswith("## "):
                break
            if line.strip() and not line.strip().startswith("<!--"):
                rule_lines.append(line.strip())
    return " ".join(rule_lines).strip()


def cmd_sync():
    """
    将所有 promoted 状态的错误记录规则自动写入各注册项目的 instruction 文件。
    - 已写入的记录（文件中含 record_id）会跳过，保证幂等。
    - 目标文件不存在或路径解析失败时打印警告，不中断其他同步。
    """
    promoted = collect_errors(status_filter=["promoted"])
    if not promoted:
        print("No promoted records to sync.")
        return

    projects = _parse_projects()
    if not projects:
        print("No projects registered. See memory/projects.md")
        return

    synced = 0
    skipped = 0

    for record in promoted:
        raw_path = record.get("promoted_to", "").strip('"').strip("'")
        if not raw_path:
            continue
        # Strip trailing annotation like "(Gotchas)"
        rel_path = re.sub(r'\s*\(.*\)\s*$', '', raw_path).strip()

        # Resolve absolute target by checking each registered project root
        abs_target: Path | None = None
        for proj in projects:
            root = proj.get("root", "").strip()
            if not root:
                continue
            candidate = Path(root) / rel_path
            if candidate.exists():
                abs_target = candidate
                break

        record_id = record.get("id", "unknown")

        if not abs_target:
            print(f"  ⚠  [{record_id}] target not found: {rel_path}")
            skipped += 1
            continue

        target_content = abs_target.read_text(encoding="utf-8")

        # Idempotency check: skip if already synced
        if record_id in target_content:
            print(f"  ✓  [{record_id}] already synced → {abs_target.name}")
            skipped += 1
            continue

        rule_text = _extract_rule_text(Path(record["_file"]))
        if not rule_text:
            print(f"  ⚠  [{record_id}] no rule text found, skipping")
            skipped += 1
            continue

        gotcha_entry = (
            f"\n- **[`{record_id}`]** {rule_text}\n"
            f"  <!-- auto-synced from agents-memory -->"
        )

        if "## ⚠️ Gotchas" in target_content:
            # Insert after the Gotchas heading
            target_content = target_content.replace(
                "## ⚠️ Gotchas",
                f"## ⚠️ Gotchas\n{gotcha_entry}",
                1,
            )
        else:
            target_content += f"\n\n## ⚠️ Gotchas\n{gotcha_entry}\n"

        abs_target.write_text(target_content, encoding="utf-8")
        print(f"  ✅ [{record_id}] synced → {abs_target}")
        synced += 1

    print(f"\nSync complete: {synced} synced, {skipped} skipped.")


def cmd_bridge_install(project_id: str):
    """
    在指定注册项目中安装 bridge instruction 文件。
    Bridge instruction 告诉该项目的 agent：
      - session 开始时加载 index.md（热区）
      - 代码出错后调用 CLI 或 MCP 记录错误

    前提：
      - 项目已在 memory/projects.md 中注册
      - templates/agents-memory-bridge.instructions.md 存在

    用法: python3 memory.py bridge-install synapse-network
    """
    projects = _parse_projects()
    proj = next((p for p in projects if p["id"] == project_id), None)
    if not proj:
        print(f"Project '{project_id}' not registered. Add it to memory/projects.md first.")
        return

    template_path = TEMPLATES_DIR / "agents-memory-bridge.instructions.md"
    if not template_path.exists():
        print(f"Bridge template not found: {template_path}")
        print("Run this tool after the template has been created.")
        return

    root = proj.get("root", "").strip()
    bridge_rel = proj.get("bridge_instruction", ".github/instructions/agents-memory-bridge.instructions.md").strip()
    if not root or not bridge_rel:
        print(f"Missing 'root' or 'bridge_instruction' in project registry for '{project_id}'.")
        return

    dest = Path(root) / bridge_rel
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        print(f"Already installed: {dest}")
        print("Delete the file manually if you want to reinstall.")
        return

    content = template_path.read_text(encoding="utf-8")
    dest.write_text(content, encoding="utf-8")
    print(f"✅ Bridge instruction installed → {dest}")
    print(f"Next: add it to {root}/AGENTS.md read-order or .github/instructions/ references.")


# ─── 一键注册 ────────────────────────────────────────────────────────────────

# 候选 instruction 文件名关键词 → domain 映射
_DOMAIN_HINTS: list[tuple[str, str]] = [
    ("finance-backend",  "finance"),
    ("finance-admin",    "finance"),
    ("finance",          "finance"),
    ("python",           "python"),
    ("frontend",         "frontend"),
    ("admin-console",    "frontend"),
    ("docs",             "docs"),
    ("config",           "config"),
    ("infra",            "infra"),
    ("safety",           "config"),
]


def _detect_project_id(root: Path) -> str:
    """从 git remote URL 或目录名推断项目 ID。"""
    import subprocess
    try:
        url = subprocess.check_output(
            ["git", "-C", str(root), "remote", "get-url", "origin"],
            stderr=subprocess.DEVNULL, text=True,
        ).strip()
        # github.com:owner/repo.git  or  https://github.com/owner/repo.git
        repo_name = re.split(r"[/:]" , url.rstrip(".git").rstrip("/"))[-1]
        return repo_name.lower().replace("_", "-")
    except Exception:
        return root.name.lower().replace("_", "-")


def _detect_domains(instruction_dir: Path) -> list[str]:
    """扫描 instruction_dir 中的 .instructions.md 文件，推断涉及的 domain 列表。"""
    if not instruction_dir.exists():
        return ["python", "docs"]
    found: set[str] = set()
    for f in instruction_dir.glob("*.instructions.md"):
        name = f.name.lower()
        for hint, domain in _DOMAIN_HINTS:
            if hint in name:
                found.add(domain)
    return sorted(found) if found else ["python", "docs"]


def _detect_instruction_files(instruction_dir: Path, root: Path) -> dict[str, str]:
    """返回 domain → relative-path 映射（只包含真实存在的文件）。"""
    mapping: dict[str, str] = {}
    if not instruction_dir.exists():
        return mapping
    for f in sorted(instruction_dir.glob("*.instructions.md")):
        name = f.name.lower()
        for hint, domain in _DOMAIN_HINTS:
            if hint in name and domain not in mapping:
                rel = f.relative_to(root)
                mapping[domain] = str(rel)
    return mapping


def _project_already_registered(project_id: str) -> bool:
    """检查 projects.md 中是否已包含该项目 ID。"""
    if not PROJECTS_FILE.exists():
        return False
    return f"## {project_id}" in PROJECTS_FILE.read_text(encoding="utf-8")


def _append_project_entry(entry: str):
    """将新项目条目追加到 projects.md 末尾（自动插在 '注册新项目' 说明之前）."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    if not PROJECTS_FILE.exists():
        PROJECTS_FILE.write_text("# Project Registry\n\n", encoding="utf-8")
    content = PROJECTS_FILE.read_text(encoding="utf-8")
    # Insert before the '## 注册新项目' section if it exists
    marker = "## 注册新项目"
    if marker in content:
        content = content.replace(marker, entry + "\n" + marker, 1)
    else:
        content = content.rstrip() + "\n\n" + entry + "\n"
    PROJECTS_FILE.write_text(content, encoding="utf-8")


def cmd_register(path: str = "."):
    """
    一键注册新项目到 Agents-Memory 共享记忆系统，并自动安装 bridge instruction。

    步骤：
      1. 解析项目根目录（默认当前目录）
      2. 从 git remote / 目录名自动推断项目 ID
      3. 扫描 .github/instructions/ 自动检测 domains 和 instruction_files
      4. 写入 memory/projects.md
      5. 安装 bridge instruction（可选）

    用法:
      python3 /path/to/scripts/memory.py register               # 注册当前目录
      python3 /path/to/scripts/memory.py register /path/to/proj  # 注册指定路径
    """
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        print(f"路径不存在: {root}")
        return

    # ── 1. 推断项目 ID ──────────────────────────────────────────────────────
    detected_id = _detect_project_id(root)
    print(f"\n🔍 检测到项目 ID: {detected_id}  (来源: git remote / 目录名)")
    project_id = input(f"Project ID [{detected_id}]: ").strip() or detected_id
    project_id = project_id.lower().replace("_", "-")

    if _project_already_registered(project_id):
        print(f"⚠️  '{project_id}' 已在 memory/projects.md 中注册，跳过写入。")
        print("如需更新，请手动编辑 memory/projects.md。")
        _offer_bridge_install(project_id)
        _offer_mcp_setup(project_id, root)
        return

    # ── 2. 检测 instruction 目录 ────────────────────────────────────────────
    default_instr_dir = ".github/instructions"
    instr_dir_input = input(f"Instruction 目录 [{default_instr_dir}]: ").strip() or default_instr_dir
    instr_dir_abs = root / instr_dir_input

    # ── 3. 自动推断 domain + instruction_files ──────────────────────────────
    domains = _detect_domains(instr_dir_abs)
    instr_files = _detect_instruction_files(instr_dir_abs, root)

    print(f"\n📂 扫描到 instruction 文件:")
    if instr_files:
        for d, p in instr_files.items():
            print(f"   {d:<12} → {p}")
    else:
        print("   (未找到 .instructions.md 文件，将使用空映射)")
    print(f"\n🏷  推断的 domains: {', '.join(domains)}")
    domains_input = input(f"Domains (逗号分隔) [{', '.join(domains)}]: ").strip()
    if domains_input:
        domains = [d.strip() for d in domains_input.split(",") if d.strip()]

    # ── 4. 组装 projects.md 条目 ────────────────────────────────────────────
    bridge_rel = f"{instr_dir_input}/agents-memory-bridge.instructions.md"
    instr_lines = ""
    if instr_files:
        instr_lines = "- **instruction_files**:\n"
        for d, p in instr_files.items():
            instr_lines += f"  - {d:<12}: {p}\n"

    entry = (
        f"## {project_id}\n\n"
        f"- **id**: {project_id}\n"
        f"- **root**: {root}\n"
        f"- **instruction_dir**: {instr_dir_input}\n"
        f"- **bridge_instruction**: {bridge_rel}\n"
        f"- **active**: true\n"
        f"- **domains**: {', '.join(domains)}\n"
        f"{instr_lines}"
        f"\n---\n"
    )

    _append_project_entry(entry)
    print(f"\n✅ 已写入 memory/projects.md → {project_id}")

    # ── 5. 安装 bridge instruction ──────────────────────────────────────────
    _offer_bridge_install(project_id)

    # ── 6. 写入 .vscode/mcp.json ─────────────────────────────────────────
    _offer_mcp_setup(project_id, root)


def _offer_mcp_setup(project_id: str, project_root: Path):
    """询问并写入 .vscode/mcp.json。"""
    mcp_file = project_root / ".vscode" / "mcp.json"
    import json
    already_has = False
    if mcp_file.exists():
        try:
            already_has = "agents-memory" in json.loads(mcp_file.read_text(encoding="utf-8")).get("servers", {})
        except Exception:
            pass

    if already_has:
        print(f"\nℹ️  .vscode/mcp.json 已包含 agents-memory 配置，跳过。")
        return

    answer = input("\n自动写入 .vscode/mcp.json（VS Code MCP 工具层）？[Y/n]: ").strip().lower()
    if answer in ("", "y", "yes"):
        _write_vscode_mcp_json(project_root)
    else:
        print(f"跳过。稍后可手动运行: amem mcp-setup {project_id}")


def _offer_bridge_install(project_id: str):
    """询问并执行 bridge instruction 安装。"""
    template_path = TEMPLATES_DIR / "agents-memory-bridge.instructions.md"
    if not template_path.exists():
        print(f"\n⚠️  Bridge 模板不存在: {template_path}，跳过安装。")
        return
    answer = input("\n自动安装 bridge instruction？[Y/n]: ").strip().lower()
    if answer in ("", "y", "yes"):
        cmd_bridge_install(project_id)
    else:
        print(f"跳过。稍后可手动运行: python3 scripts/memory.py bridge-install {project_id}")


def _write_vscode_mcp_json(project_root: Path) -> bool:
    """
    在目标项目写入 .vscode/mcp.json，让 VS Code 知道 MCP Server 在哪里。
    如果文件已存在且包含 'agents-memory' 键，跳过（幂等）。
    如果 ".vscode/mcp.json" 存在但不含 agents-memory，将 server 条目 merge 进去。
    """
    vscode_dir = project_root / ".vscode"
    mcp_file   = vscode_dir / "mcp.json"
    server_entry = {
        "type": "stdio",
        "command": "python3.12",
        "args": [str(BASE_DIR / "scripts" / "mcp_server.py")],
        "env": {},
    }

    import json

    if mcp_file.exists():
        try:
            existing = json.loads(mcp_file.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
        if "agents-memory" in existing.get("servers", {}):
            print(f"  已存在: {mcp_file}")
            return False
        # Merge
        existing.setdefault("servers", {})["agents-memory"] = server_entry
        mcp_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  ✅ 已合并写入 agents-memory server 条目 → {mcp_file}")
        return True

    # 新建
    vscode_dir.mkdir(exist_ok=True)
    config = {"servers": {"agents-memory": server_entry}}
    mcp_file.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  ✅ 已写入 {mcp_file}")
    return True


def cmd_mcp_setup(project_id_or_path: str = "."):
    """
    在已注册项目中写入 .vscode/mcp.json，将 Agents-Memory MCP Server 接入 VS Code。

    用法:
      amem mcp-setup                   # 将当前目录项目配置
      amem mcp-setup synapse-network   # 通过已注册项目 ID 配置
      amem mcp-setup /abs/path         # 通过绝对路径配置
    """
    import json

    # 判断是 ID、路径还是""（当前目录）
    candidate = Path(project_id_or_path).expanduser().resolve()
    if candidate.is_dir():
        project_root = candidate
    else:
        # 当作项目 ID 查找
        projects = _parse_projects()
        proj = next((p for p in projects if p["id"] == project_id_or_path), None)
        if not proj:
            print(f"项目 '{project_id_or_path}' 未注册且不是有效路径。")
            print("先运行: amem register")
            return
        project_root = Path(proj["root"])

    print(f"\n🛠  写入 .vscode/mcp.json → {project_root}")
    _write_vscode_mcp_json(project_root)
    print()
    print("验证方式：在该项目的 VS Code Agent/Chat 面板中输入：")
    print('  请调用 memory_get_index 工具，告诉我当前有多少条错误记录。')



# ─── 入口 ────────────────────────────────────────────────────────────────────

def main():
    ERRORS_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    args = sys.argv[1:]

    if not args or args[0] == "list":
        cmd_list()
    elif args[0] == "stats":
        cmd_stats()
    elif args[0] == "search":
        cmd_search(" ".join(args[1:]) if len(args) > 1 else "")
    elif args[0] == "vsearch":
        if len(args) < 2:
            print("用法: python3 memory.py vsearch <query>")
        else:
            top_k = int(args[-1]) if args[-1].isdigit() else 5
            query = " ".join(args[1:]) if not args[-1].isdigit() else " ".join(args[1:-1])
            cmd_vsearch(query, top_k)
    elif args[0] == "embed":
        cmd_embed()
    elif args[0] == "to-qdrant":
        cmd_to_qdrant()
    elif args[0] == "sync":
        cmd_sync()
    elif args[0] == "bridge-install":
        cmd_bridge_install(args[1]) if len(args) > 1 else print("用法: python3 memory.py bridge-install <project-id>")
    elif args[0] == "mcp-setup":
        cmd_mcp_setup(args[1] if len(args) > 1 else ".")
    elif args[0] == "register":
        cmd_register(args[1] if len(args) > 1 else ".")
    elif args[0] == "promote":
        cmd_promote(args[1]) if len(args) > 1 else print("用法: python3 memory.py promote <id>")
    elif args[0] == "archive":
        cmd_archive()
    elif args[0] == "update-index":
        cmd_update_index()
    elif args[0] == "new":
        cmd_new()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
