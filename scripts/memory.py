#!/usr/bin/env python3
"""
Agents-Memory CLI — 错误记录管理工具

用法:
  python memory.py new               # 交互式创建新错误记录
  python memory.py list              # 列出所有 new/reviewed 状态的记录
  python memory.py stats             # 统计各类别错误数量
  python memory.py search <keyword>  # 关键词搜索错误记录
  python memory.py promote <id>      # 将错误记录标记为 promoted
  python memory.py archive           # 归档超过 90 天且无重复的记录
  python memory.py update-index      # 重新生成 index.md 的统计数字
"""

import os
import sys
import glob
import json
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
ERRORS_DIR = BASE_DIR / "errors"
ARCHIVE_DIR = BASE_DIR / "errors" / "archive"
MEMORY_DIR = BASE_DIR / "memory"
INDEX_FILE = BASE_DIR / "index.md"

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


def parse_frontmatter(filepath: Path) -> dict:
    """Parse YAML-ish frontmatter from a markdown file (simple key: value only)."""
    meta = {}
    with open(filepath) as f:
        lines = f.readlines()
    in_front = False
    for line in lines:
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


def collect_errors(status_filter=None) -> list[dict]:
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


def cmd_list():
    records = collect_errors(status_filter=["new", "reviewed"])
    if not records:
        print("No active error records found.")
        return
    print(f"\n{'ID':<35} {'Project':<20} {'Category':<18} {'Sev':<10} {'Status'}")
    print("-" * 95)
    for r in records:
        print(f"{r.get('id',''):<35} {r.get('project',''):<20} {r.get('category',''):<18} {r.get('severity',''):<10} {r.get('status','')}")
    print(f"\nTotal: {len(records)} active records")


def cmd_stats():
    records = collect_errors()
    if not records:
        print("No records found.")
        return
    from collections import Counter
    cats = Counter(r.get("category", "unknown") for r in records)
    projs = Counter(r.get("project", "unknown") for r in records)
    statuses = Counter(r.get("status", "unknown") for r in records)
    print("\n=== By Category ===")
    for cat, count in cats.most_common():
        print(f"  {cat:<22} {count}")
    print("\n=== By Project ===")
    for proj, count in projs.most_common():
        print(f"  {proj:<22} {count}")
    print("\n=== By Status ===")
    for status, count in statuses.most_common():
        print(f"  {status:<22} {count}")
    print(f"\nTotal records: {len(records)}")


def cmd_search(keyword: str):
    keyword = keyword.lower()
    matches = []
    for filepath in sorted(ERRORS_DIR.glob("*.md")):
        content = filepath.read_text().lower()
        if keyword in content:
            meta = parse_frontmatter(filepath)
            matches.append((filepath.name, meta))
    if not matches:
        print(f"No records matching '{keyword}'")
        return
    print(f"\nFound {len(matches)} match(es) for '{keyword}':\n")
    for fname, meta in matches:
        print(f"  {fname}")
        print(f"    project={meta.get('project','')} category={meta.get('category','')} status={meta.get('status','')}")


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
    instruction_path = input("Write instruction file path (e.g., .github/instructions/python.instructions.md): ").strip()
    content = matched.read_text()
    content = content.replace('status: reviewed', 'status: promoted')
    content = content.replace('promoted_to: ""', f'promoted_to: "{instruction_path}"')
    matched.write_text(content)
    print(f"Promoted {record_id} → {instruction_path}")
    cmd_update_index()


def cmd_archive():
    cutoff = date.today() - timedelta(days=90)
    ARCHIVE_DIR.mkdir(exist_ok=True)
    archived = 0
    for filepath in list(ERRORS_DIR.glob("*.md")):
        meta = parse_frontmatter(filepath)
        status = meta.get("status", "")
        repeat = int(meta.get("repeat_count", "1"))
        record_date_str = meta.get("date", "")
        if status not in ("reviewed", "promoted"):
            continue
        try:
            record_date = date.fromisoformat(record_date_str)
        except ValueError:
            continue
        if record_date < cutoff and repeat <= 1:
            dest = ARCHIVE_DIR / filepath.name
            shutil.move(str(filepath), str(dest))
            archived += 1
            print(f"  Archived: {filepath.name}")
    print(f"\n{archived} record(s) archived.")
    if archived:
        cmd_update_index()


def cmd_update_index():
    active = collect_errors(status_filter=["new", "reviewed"])
    promoted = collect_errors(status_filter=["promoted"])
    total_errors = len(list(ERRORS_DIR.glob("*.md")))

    from collections import Counter
    cats = Counter(r.get("category", "") for r in active)
    top3_cats = cats.most_common(3)

    recent_promoted = sorted(
        promoted,
        key=lambda r: r.get("date", ""),
        reverse=True
    )[:3]

    top3_cats_str = "\n".join(
        f"| `{cat}` | {count} |" for cat, count in top3_cats
    ) or "| _暂无_ | - |"

    recent_rules_str = "\n".join(
        f"- **{r.get('id','')}**: {r.get('promoted_to','')}"
        for r in recent_promoted
    ) or "_暂无_"

    index_content = f"""# Agent Memory Index — Hot Tier

> 这是 Agent 每次启动时**必须加载**的唯一文件，严格控制在 400 tokens 以内。
> 其余所有内容通过 semantic search 或按需读取。

## 当前活跃规则总数

| 类别 | 数量 | 文件 |
|------|------|------|
| 错误模式 (errors) | {total_errors} | `errors/` |
| 升级规则 (promoted) | {len(promoted)} | `memory/rules.md` |

## 最近升级的规则（Top 3）

{recent_rules_str}

## 最高频错误类别（Top 3）

| Category | Count |
|----------|-------|
{top3_cats_str}

## 检索指引

- 写代码前：查 `memory/rules.md` 匹配项目领域的规则
- 代码出错后：用错误类型关键词检索 `errors/` 目录
- 写 Finance 代码：额外加载 `memory/rules.md`（Finance 段）
- 做文档变更：检查 docs-drift 类别的错误记录

## 快速提交新错误

```
errors/YYYY-MM-DD-<project>-<sequence>.md
```

格式见 `schema/error-record.md`
"""
    INDEX_FILE.write_text(index_content)
    print("index.md updated.")


def cmd_new():
    print("\n=== New Error Record ===\n")
    today = date.today().isoformat()

    print(f"Projects: {', '.join(PROJECTS)}")
    project = input("Project: ").strip() or "other"

    # Auto-generate sequence
    existing = list(ERRORS_DIR.glob(f"{today}-{project}-*.md"))
    seq = str(len(existing) + 1).zfill(3)
    record_id = f"{today}-{project}-{seq}"
    filename = ERRORS_DIR / f"{record_id}.md"

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
    filename.write_text(content)
    print(f"\nCreated: {filename}")
    cmd_update_index()


def main():
    args = sys.argv[1:]
    if not args or args[0] == "list":
        cmd_list()
    elif args[0] == "stats":
        cmd_stats()
    elif args[0] == "search" and len(args) > 1:
        cmd_search(args[1])
    elif args[0] == "promote" and len(args) > 1:
        cmd_promote(args[1])
    elif args[0] == "archive":
        cmd_archive()
    elif args[0] == "update-index":
        cmd_update_index()
    elif args[0] == "new":
        cmd_new()
    else:
        print(__doc__)


if __name__ == "__main__":
    ERRORS_DIR.mkdir(exist_ok=True)
    ARCHIVE_DIR.mkdir(exist_ok=True)
    MEMORY_DIR.mkdir(exist_ok=True)
    main()
