#!/usr/bin/env python3.12
"""
Agents-Memory MCP Server

让任何支持 MCP 协议的 AI Agent（Claude、GitHub Copilot 等）
把 agents-memory 当作工具调用，实现全自动的共享记忆读写。

启动方式:
  python3 scripts/mcp_server.py          # stdio 模式（VS Code / Claude Desktop）

安装依赖:
  pip install mcp

VS Code 配置（.vscode/mcp.json）:
  {
    "servers": {
      "agents-memory": {
        "type": "stdio",
        "command": "python3",
        "args": ["/Users/cliff/workspace/Agents-Memory/scripts/mcp_server.py"]
      }
    }
  }

Claude Desktop 配置（~/Library/Application Support/Claude/claude_desktop_config.json）:
  {
    "mcpServers": {
      "agents-memory": {
        "command": "python3",
        "args": ["/Users/cliff/workspace/Agents-Memory/scripts/mcp_server.py"]
      }
    }
  }

暴露的工具（Tools）:
  memory_get_index()          → 读取 index.md（热区，≤400 tokens，每次 session 开始调用）
  memory_get_rules(domain)    → 读取指定领域的规则（温区）
  memory_search(query)        → 关键词搜索错误记录
  memory_record_error(...)    → 记录新错误（Agent 自动调用，无需人工）
  memory_list_projects()      → 列出已注册的项目
  memory_get_project_rules(project_id) → 获取某项目的适用规则
  memory_sync_stats()         → 返回记录数量统计（用于决定检索策略）
"""

import json
import sys
import shutil
from datetime import date, timedelta
from pathlib import Path

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("请先安装 mcp: pip install mcp", file=sys.stderr)
    sys.exit(1)

# ─── 路径 ────────────────────────────────────────────────────────────────────

BASE_DIR     = Path(__file__).parent.parent
ERRORS_DIR   = BASE_DIR / "errors"
ARCHIVE_DIR  = BASE_DIR / "errors" / "archive"
MEMORY_DIR   = BASE_DIR / "memory"
INDEX_FILE   = BASE_DIR / "index.md"
PROJECTS_FILE = MEMORY_DIR / "projects.md"
RULES_FILE   = MEMORY_DIR / "rules.md"

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

# ─── 内部工具函数 ─────────────────────────────────────────────────────────────

def _parse_frontmatter(filepath: Path) -> dict:
    meta: dict = {}
    in_front = False
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip()
            if line == "---":
                in_front = not in_front if not in_front else False
                if not in_front and meta:
                    break
                continue
            if in_front and ": " in line:
                k, _, v = line.partition(": ")
                meta[k.strip()] = v.strip().strip('"')
    return meta


def _collect_errors(status_filter: list[str] | None = None) -> list[dict]:
    records = []
    for fp in sorted(ERRORS_DIR.glob("*.md")):
        meta = _parse_frontmatter(fp)
        if not meta:
            continue
        if status_filter and meta.get("status") not in status_filter:
            continue
        meta["_file"] = str(fp)
        records.append(meta)
    return records


def _total_count() -> int:
    return len(list(ERRORS_DIR.glob("*.md")))


def _update_index():
    """更新 index.md 统计数字（每次写入新错误后调用）。"""
    # 延迟导入，避免 mcp server 启动时引入过多模块
    sys.path.insert(0, str(BASE_DIR / "scripts"))
    from memory import cmd_update_index  # type: ignore
    cmd_update_index()


# ─── MCP Server ──────────────────────────────────────────────────────────────

mcp = FastMCP(
    "agents-memory",
    instructions=(
        "Shared memory system for AI Agents. "
        "Always call memory_get_index() at the start of a session involving code changes. "
        "Call memory_record_error() whenever you find and fix a bug or make an error during coding. "
        "Call memory_get_rules(domain) before working on finance, frontend, or python code."
    ),
)


# ── Read tools ────────────────────────────────────────────────────────────────

@mcp.tool()
def memory_get_index() -> str:
    """
    Get the hot-tier memory index (≤ 400 tokens).
    ALWAYS call this at the start of every coding session.
    Returns: summary of active error count, promoted rules, top error categories, and search guidance.
    """
    if not INDEX_FILE.exists():
        return "Memory index not found. Run: python3 scripts/memory.py update-index"
    return INDEX_FILE.read_text(encoding="utf-8")


@mcp.tool()
def memory_get_rules(domain: str = "") -> str:
    """
    Get prevention rules from the warm-tier memory.
    Call this before working on code in a specific domain to load relevant gotchas.

    Args:
        domain: One of: finance, frontend, python, docs, config, infra.
                Leave empty to get all rules.

    Returns: Promoted rules relevant to the domain.
    """
    if not RULES_FILE.exists():
        return "No rules file found."
    content = RULES_FILE.read_text(encoding="utf-8")
    if not domain:
        return content

    # Extract only the relevant section
    domain_map = {
        "python":   ["## Python", "## Python / FastAPI"],
        "finance":  ["## Finance"],
        "frontend": ["## TypeScript", "## TypeScript / Frontend"],
        "docs":     ["## Docs"],
        "config":   ["## Docs / Config"],
    }
    headers = domain_map.get(domain.lower(), [])
    if not headers:
        return content  # return all if domain not mapped

    lines = content.splitlines()
    result_lines: list[str] = []
    in_section = False
    for line in lines:
        if any(line.startswith(h) for h in headers):
            in_section = True
        elif line.startswith("## ") and in_section:
            break
        if in_section:
            result_lines.append(line)

    return "\n".join(result_lines) if result_lines else f"No rules found for domain: {domain}"


@mcp.tool()
def memory_search(query: str, limit: int = 5) -> str:
    """
    Search error records by keyword.
    Use this BEFORE writing code to check if similar errors have been seen before.

    Args:
        query: Keyword or phrase to search for (case-insensitive).
        limit: Maximum number of results to return (default: 5).

    Returns: Matching error record summaries with ID, project, category, and status.
    """
    keyword = query.lower()
    matches = []
    for fp in sorted(ERRORS_DIR.glob("*.md")):
        content = fp.read_text(encoding="utf-8").lower()
        if keyword in content:
            meta = _parse_frontmatter(fp)
            if meta:
                matches.append(meta)
        if len(matches) >= limit:
            break

    if not matches:
        return f"No error records matching '{query}'."

    lines = [f"Found {len(matches)} match(es) for '{query}':\n"]
    for m in matches:
        lines.append(
            f"• {m.get('id','')}  [{m.get('severity','')}]  "
            f"{m.get('project','')} / {m.get('category','')}  "
            f"→ status: {m.get('status','')}"
        )
    return "\n".join(lines)


@mcp.tool()
def memory_get_error(record_id: str) -> str:
    """
    Get the full content of a specific error record by ID.

    Args:
        record_id: The error record ID (e.g., 2026-03-26-spec2flow-001)

    Returns: Full markdown content of the error record.
    """
    for fp in ERRORS_DIR.glob("*.md"):
        meta = _parse_frontmatter(fp)
        if meta.get("id") == record_id:
            return fp.read_text(encoding="utf-8")
    return f"Error record '{record_id}' not found."


@mcp.tool()
def memory_list_projects() -> str:
    """
    List all projects registered in the shared memory system.
    Returns: Project registry with IDs, paths, and active domains.
    """
    if not PROJECTS_FILE.exists():
        return "No projects registered. See memory/projects.md"
    return PROJECTS_FILE.read_text(encoding="utf-8")


@mcp.tool()
def memory_sync_stats() -> str:
    """
    Get current memory statistics to decide search strategy.
    Returns: record count, search recommendation (keyword vs semantic), and storage backend.
    """
    total = _total_count()
    active = _collect_errors(status_filter=["new", "reviewed"])
    promoted = _collect_errors(status_filter=["promoted"])
    strategy = "semantic (LanceDB)" if total >= 200 else "keyword (stdlib)"
    return json.dumps({
        "total_records":    total,
        "active_records":   len(active),
        "promoted_rules":   len(promoted),
        "search_strategy":  strategy,
        "vector_threshold": 200,
    }, ensure_ascii=False, indent=2)


# ── Write tools ───────────────────────────────────────────────────────────────

@mcp.tool()
def memory_record_error(
    project:    str,
    domain:     str,
    category:   str,
    severity:   str,
    task:       str,
    error_desc: str,
    root_cause: str,
    fix:        str,
    rule:       str,
    file_path:  str = "",
    tags:       str = "",
) -> str:
    """
    Record a new error to the shared memory. Call this whenever you:
    - Fix a bug that took more than one attempt
    - Encounter a type error, architecture violation, or unexpected behavior
    - Make a mistake that could recur in future sessions

    Args:
        project:    Project ID. One of: synapse-network, spec2flow, provider-service,
                    gateway, admin-front, gateway-admin, other
        domain:     Code domain. One of: finance, frontend, python, docs, config, infra, other
        category:   Error type. One of: type-error, logic-error, finance-safety, arch-violation,
                    test-failure, docs-drift, config-error, build-error, runtime-error, security
        severity:   critical | warning | info
        task:       What you were trying to accomplish (1 sentence)
        error_desc: What went wrong (1-2 sentences, include error message if any)
        root_cause: Why it happened (1-2 sentences)
        fix:        How it was fixed (1-2 sentences)
        rule:       Prevention rule derived from this error (1-2 sentences, imperative form)
        file_path:  Affected file path (optional)
        tags:       Comma-separated keywords (optional)

    Returns: Created record ID and file path.
    """
    ERRORS_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()

    # validate enums loosely
    if project not in PROJECTS:
        project = "other"
    if domain not in DOMAINS:
        domain = "other"
    if category not in CATEGORIES:
        category = "runtime-error"
    if severity not in ("critical", "warning", "info"):
        severity = "warning"

    existing = list(ERRORS_DIR.glob(f"{today}-{project}-*.md"))
    seq = str(len(existing) + 1).zfill(3)
    record_id = f"{today}-{project}-{seq}"
    filepath = ERRORS_DIR / f"{record_id}.md"

    tags_value = f"[{', '.join(t.strip() for t in tags.split(',') if t.strip())}]" if tags else "[]"
    file_line = f"- `{file_path}`" if file_path else "<!-- 填写文件路径 -->"

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
tags: {tags_value}
---

## 错误上下文

**任务目标：**
{task}

**出错文件 / 位置：**
{file_line}

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
    filepath.write_text(content, encoding="utf-8")

    # update index in background (best-effort)
    try:
        _update_index()
    except Exception:
        pass

    return (
        f"✅ Error recorded: {record_id}\n"
        f"File: {filepath}\n"
        f"Next step: Run `python3 scripts/memory.py promote {record_id}` "
        f"when repeat_count reaches 2 or severity is critical."
    )


@mcp.tool()
def memory_increment_repeat(record_id: str) -> str:
    """
    Increment the repeat_count of an existing error record.
    Call this when you encounter the SAME error pattern in a new session
    (instead of creating a duplicate record).

    Args:
        record_id: The error record ID to increment.

    Returns: Updated repeat_count and whether the promote threshold was reached.
    """
    for fp in ERRORS_DIR.glob("*.md"):
        meta = _parse_frontmatter(fp)
        if meta.get("id") == record_id:
            content = fp.read_text(encoding="utf-8")
            old_count = int(meta.get("repeat_count", "1"))
            new_count = old_count + 1
            content = content.replace(
                f"repeat_count: {old_count}",
                f"repeat_count: {new_count}",
            )
            fp.write_text(content, encoding="utf-8")
            should_promote = new_count >= 2 or meta.get("severity") == "critical"
            msg = f"repeat_count updated: {old_count} → {new_count}"
            if should_promote and meta.get("status") == "reviewed":
                msg += f"\n⚡ Promote threshold reached! Run: python3 scripts/memory.py promote {record_id}"
            return msg
    return f"Record '{record_id}' not found."


# ─── 入口 ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
