from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("请先安装 mcp: pip install mcp", file=sys.stderr)
    sys.exit(1)

from agents_memory.constants import CATEGORIES, DOMAINS, PROJECTS, VECTOR_THRESHOLD
from agents_memory.logging_utils import log_file_update
from agents_memory.runtime import build_context
from agents_memory.services.integration import load_onboarding_state
from agents_memory.services.projects import parse_projects
from agents_memory.services.records import cmd_update_index, parse_frontmatter

ctx = build_context(logger_name="agents_memory.mcp", reference_file=__file__)


def _log_tool_start(tool_name: str, **fields: object) -> None:
    payload = " | ".join(f"{key}={value}" for key, value in fields.items() if value not in (None, ""))
    suffix = f" | {payload}" if payload else ""
    ctx.logger.info("tool_start | tool=%s%s", tool_name, suffix)


def _log_tool_end(tool_name: str, **fields: object) -> None:
    payload = " | ".join(f"{key}={value}" for key, value in fields.items() if value not in (None, ""))
    suffix = f" | {payload}" if payload else ""
    ctx.logger.info("tool_end | tool=%s%s", tool_name, suffix)


mcp = FastMCP(
    "agents-memory",
    instructions=(
        "Shared memory system for AI Agents. Always call memory_get_index() at the start of a session involving code changes. "
        "Call memory_get_onboarding_state() before deep implementation if onboarding-state.json is available. "
        "Call memory_record_error() whenever you find and fix a bug or make an error during coding. "
        "Call memory_get_rules(domain) before working on finance, frontend, or python code."
    ),
)


@mcp.tool()
def memory_get_index() -> str:
    _log_tool_start("memory_get_index")
    if not ctx.index_file.exists():
        _log_tool_end("memory_get_index", status="missing_index")
        return "Memory index not found. Run: python3 scripts/memory.py update-index"
    _log_tool_end("memory_get_index", status="ok")
    return ctx.index_file.read_text(encoding="utf-8")


@mcp.tool()
def memory_get_onboarding_state(project_root: str = ".") -> str:
    _log_tool_start("memory_get_onboarding_state", project_root=project_root)
    target_root = Path(project_root).expanduser().resolve()
    state = load_onboarding_state(target_root)
    if state is None:
        _log_tool_end("memory_get_onboarding_state", status="missing", project_root=target_root)
        return (
            f"No onboarding state found at {target_root / '.agents-memory' / 'onboarding-state.json'}.\n"
            "Run: python3 scripts/memory.py doctor . --write-state --write-checklist"
        )
    _log_tool_end("memory_get_onboarding_state", status="ok", project_root=target_root)
    return json.dumps(state, ensure_ascii=False, indent=2)


@mcp.tool()
def memory_get_rules(domain: str = "") -> str:
    _log_tool_start("memory_get_rules", domain=domain or "all")
    if not ctx.rules_file.exists():
        _log_tool_end("memory_get_rules", status="missing_rules")
        return "No rules file found."
    content = ctx.rules_file.read_text(encoding="utf-8")
    if not domain:
        _log_tool_end("memory_get_rules", status="ok", scope="all")
        return content
    domain_map = {
        "python": ["## Python", "## Python / FastAPI"],
        "finance": ["## Finance"],
        "frontend": ["## TypeScript", "## TypeScript / Frontend"],
        "docs": ["## Docs"],
        "config": ["## Docs / Config"],
    }
    headers = domain_map.get(domain.lower(), [])
    if not headers:
        _log_tool_end("memory_get_rules", status="ok", scope="all_unmapped")
        return content
    result_lines: list[str] = []
    in_section = False
    for line in content.splitlines():
        if any(line.startswith(header) for header in headers):
            in_section = True
        elif line.startswith("## ") and in_section:
            break
        if in_section:
            result_lines.append(line)
    result = "\n".join(result_lines) if result_lines else f"No rules found for domain: {domain}"
    _log_tool_end("memory_get_rules", status="ok", scope=domain)
    return result


@mcp.tool()
def memory_search(query: str, limit: int = 5) -> str:
    _log_tool_start("memory_search", query=query, limit=limit)
    keyword = query.lower()
    matches = []
    for filepath in sorted(ctx.errors_dir.glob("*.md")):
        content = filepath.read_text(encoding="utf-8").lower()
        if keyword in content:
            meta = parse_frontmatter(filepath)
            if meta:
                matches.append(meta)
        if len(matches) >= limit:
            break
    if not matches:
        _log_tool_end("memory_search", status="no_matches", query=query)
        return f"No error records matching '{query}'."
    lines = [f"Found {len(matches)} match(es) for '{query}':\n"]
    for match in matches:
        lines.append(f"• {match.get('id', '')}  [{match.get('severity', '')}]  {match.get('project', '')} / {match.get('category', '')}  → status: {match.get('status', '')}")
    _log_tool_end("memory_search", status="ok", query=query, matches=len(matches))
    return "\n".join(lines)


@mcp.tool()
def memory_get_error(record_id: str) -> str:
    _log_tool_start("memory_get_error", record_id=record_id)
    for filepath in ctx.errors_dir.glob("*.md"):
        meta = parse_frontmatter(filepath)
        if meta.get("id") == record_id:
            _log_tool_end("memory_get_error", status="ok", record_id=record_id)
            return filepath.read_text(encoding="utf-8")
    _log_tool_end("memory_get_error", status="not_found", record_id=record_id)
    return f"Record '{record_id}' not found."


@mcp.tool()
def memory_record_error(project: str, domain: str, category: str, severity: str, task: str, error_desc: str, root_cause: str, fix: str, rule: str, file_path: str = "", tags: str = "") -> str:
    _log_tool_start("memory_record_error", project=project, category=category, severity=severity)
    if project not in PROJECTS:
        return f"Invalid project: {project}. Must be one of: {', '.join(PROJECTS)}"
    if domain not in DOMAINS:
        return f"Invalid domain: {domain}. Must be one of: {', '.join(DOMAINS)}"
    if category not in CATEGORIES:
        return f"Invalid category: {category}. Must be one of: {', '.join(CATEGORIES)}"
    if severity not in {"critical", "warning", "info"}:
        return "Invalid severity. Must be one of: critical, warning, info"

    today = date.today().isoformat()
    existing = list(ctx.errors_dir.glob(f"{today}-{project}-*.md"))
    seq = str(len(existing) + 1).zfill(3)
    record_id = f"{today}-{project}-{seq}"
    filename = ctx.errors_dir / f"{record_id}.md"
    tag_items = [item.strip() for item in tags.split(",") if item.strip()]
    file_section = file_path if file_path else "<!-- 填写文件路径 -->"
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
tags: [{', '.join(tag_items)}]
---

## 错误上下文

**任务目标：**
{task}

**出错文件 / 位置：**
{file_section}

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
    ctx.ensure_storage_dirs()
    filename.write_text(content, encoding="utf-8")
    log_file_update(ctx.logger, action="create_error_record", path=filename, detail=f"record_id={record_id}")
    cmd_update_index(ctx)
    _log_tool_end("memory_record_error", status="ok", record_id=record_id)
    return f"✅ Error recorded: {record_id}\nFile: {filename}\nNext step: Run `python3 scripts/memory.py promote {record_id}` when repeat_count reaches 2 or severity is critical."


@mcp.tool()
def memory_increment_repeat(record_id: str) -> str:
    _log_tool_start("memory_increment_repeat", record_id=record_id)
    for filepath in ctx.errors_dir.glob("*.md"):
        meta = parse_frontmatter(filepath)
        if meta.get("id") != record_id:
            continue
        current = int(meta.get("repeat_count", "1"))
        updated = filepath.read_text(encoding="utf-8").replace(f"repeat_count: {current}", f"repeat_count: {current + 1}", 1)
        filepath.write_text(updated, encoding="utf-8")
        log_file_update(ctx.logger, action="increment_repeat", path=filepath, detail=f"record_id={record_id};repeat_count={current + 1}")
        cmd_update_index(ctx)
        promoted = current + 1 >= 2
        _log_tool_end("memory_increment_repeat", status="ok", record_id=record_id, repeat_count=current + 1)
        return f"✅ Updated repeat_count: {record_id} → {current + 1}\nPromote threshold reached: {'yes' if promoted else 'no'}"
    _log_tool_end("memory_increment_repeat", status="not_found", record_id=record_id)
    return f"Record '{record_id}' not found."


@mcp.tool()
def memory_list_projects() -> str:
    _log_tool_start("memory_list_projects")
    projects = parse_projects(ctx)
    if not projects:
        _log_tool_end("memory_list_projects", status="empty")
        return "No registered projects found."
    lines = ["Registered projects:\n"]
    for project in projects:
        lines.append(f"• {project.get('id', '')}  →  {project.get('root', '')}")
    _log_tool_end("memory_list_projects", status="ok", count=len(projects))
    return "\n".join(lines)


@mcp.tool()
def memory_sync_stats() -> str:
    _log_tool_start("memory_sync_stats")
    count = len(list(ctx.errors_dir.glob("*.md")))
    recommendation = "keyword search" if count < VECTOR_THRESHOLD else "semantic search"
    backend = "local markdown + optional LanceDB/Qdrant"
    _log_tool_end("memory_sync_stats", status="ok", count=count)
    return f"Records: {count}\nRecommended search: {recommendation}\nStorage backend: {backend}"


def main() -> None:
    mcp.run()
