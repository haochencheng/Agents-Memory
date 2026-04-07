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
from agents_memory.runtime import AppContext, build_context
from agents_memory.services.integration import _merge_refactor_followup_state, execute_onboarding_next_action, load_onboarding_state, onboarding_next_action, onboarding_state_path
from agents_memory.services.planning import init_refactor_bundle
from agents_memory.services.projects import parse_projects
from agents_memory.services.records import cmd_update_index, parse_frontmatter
from agents_memory.services.validation import collect_refactor_watch_hotspots, serialize_refactor_hotspot
from agents_memory.services.wiki import list_wiki_topics, search_wiki, write_wiki_page
from agents_memory.services.wiki_compile import compile_wiki_topic

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
        "Call memory_get_onboarding_next_action() before deep implementation if onboarding-state.json is available. "
        "Call memory_execute_onboarding_next_action() when onboarding state already tells you the first required action and you want the system to execute, verify, and write back the result. "
        "Call memory_get_refactor_hotspots() when you need a structured hotspot list without relying on doctor artifacts. "
        "Call memory_init_refactor_bundle() when doctor/refactor_watch identifies a hotspot and you want the system to materialize a refactor plan bundle automatically. "
        "Call memory_record_error() whenever you find and fix a bug or make an error during coding. "
        "Call memory_get_rules(domain) before working on finance, frontend, or python code. "
        "Call memory_wiki_query(query) before starting a task to retrieve synthesized rules and context from the wiki. "
        "Call memory_wiki_update(topic, content) after completing a task to capture learnings, refined rules, or error patterns."
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
def memory_get_onboarding_next_action(project_root: str = ".") -> str:
    _log_tool_start("memory_get_onboarding_next_action", project_root=project_root)
    target_root = Path(project_root).expanduser().resolve()
    payload = onboarding_next_action(target_root)
    _log_tool_end("memory_get_onboarding_next_action", status=payload.get("status"), project_root=target_root)
    return json.dumps(payload, ensure_ascii=False, indent=2)


@mcp.tool()
def memory_execute_onboarding_next_action(project_root: str = ".", verify: bool = True, approve_unsafe: bool = False) -> str:
    _log_tool_start("memory_execute_onboarding_next_action", project_root=project_root, verify=verify, approve_unsafe=approve_unsafe)
    target_root = Path(project_root).expanduser().resolve()
    payload = execute_onboarding_next_action(ctx, target_root, verify=verify, approve_unsafe=approve_unsafe, refresh_artifacts=True)
    _log_tool_end("memory_execute_onboarding_next_action", status=payload.get("status"), project_root=target_root, verify=verify, approve_unsafe=approve_unsafe)
    return json.dumps(payload, ensure_ascii=False, indent=2)


@mcp.tool()
def memory_get_refactor_hotspots(project_root: str = ".") -> str:
    _log_tool_start("memory_get_refactor_hotspots", project_root=project_root)
    target_root = Path(project_root).expanduser().resolve()
    hotspots = collect_refactor_watch_hotspots(target_root)
    payload = {
        "status": "ok",
        "project_root": str(target_root),
        "hotspot_count": len(hotspots),
        "hotspots": [serialize_refactor_hotspot(hotspot) for hotspot in hotspots],
    }
    _log_tool_end(
        "memory_get_refactor_hotspots",
        status="ok",
        project_root=target_root,
        hotspot_count=len(hotspots),
    )
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _write_refactor_bundle_state(
    ctx: AppContext,
    target_root: Path,
    result: object,
    hotspot_payload: dict,
) -> tuple[str, object]:
    # Merge follow-up state and persist it; returns (state_path_str, recommended_followup).
    existing_state = load_onboarding_state(target_root)
    updated_state = _merge_refactor_followup_state(
        existing_state,
        project_root=target_root,
        plan_root=result.plan_root,
        hotspot_index=result.hotspot_index,
        hotspot_token=result.hotspot_token,
        hotspot=hotspot_payload,
        task_name=result.task_name,
        task_slug=result.task_slug,
    )
    state_path = onboarding_state_path(target_root)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(updated_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log_file_update(ctx.logger, action="write_refactor_followup_state", path=state_path, detail=f"project_root={target_root};task_slug={result.task_slug}")
    return str(state_path), updated_state.get("recommended_refactor_bundle")


def _init_refactor_bundle_payload(
    ctx: AppContext,
    target_root: Path,
    result: object,
    dry_run: bool,
) -> dict:
    # Build the success payload dict and optionally persist refactor follow-up state.
    payload: dict = {
        "status": "ok",
        "project_root": str(result.target_root),
        "plan_root": str(result.plan_root),
        "task_name": result.task_name,
        "task_slug": result.task_slug,
        "hotspot_index": result.hotspot_index,
        "hotspot_token": result.hotspot_token,
        "hotspot": serialize_refactor_hotspot(result.hotspot),
        "wrote_files": result.wrote_files,
        "refreshed_files": result.refreshed_files,
        "skipped_files": result.skipped_files,
        "dry_run": result.dry_run,
        "recommended_next_command": "amem doctor .",
    }
    if not dry_run:
        state_path, followup = _write_refactor_bundle_state(ctx, target_root, result, payload["hotspot"])
        payload["state_path"] = state_path
        payload["recommended_followup"] = followup
    return payload


@mcp.tool()
def memory_init_refactor_bundle(project_root: str = ".", hotspot_index: int = 1, hotspot_token: str = "", task_slug: str = "", dry_run: bool = False) -> str:
    # Initialize a refactor plan bundle for the top-ranked (or specified) hotspot.
    _log_tool_start(
        "memory_init_refactor_bundle",
        project_root=project_root,
        hotspot_index=hotspot_index,
        hotspot_token=hotspot_token,
        task_slug=task_slug,
        dry_run=dry_run,
    )
    target_root = Path(project_root).expanduser().resolve()
    try:
        result = init_refactor_bundle(
            ctx,
            target_root,
            hotspot_index=hotspot_index,
            hotspot_token=hotspot_token or None,
            task_slug=task_slug or None,
            dry_run=dry_run,
        )
    except FileNotFoundError as exc:
        payload = {"status": "missing", "project_root": str(target_root), "message": str(exc), "recommended_command": "python3 scripts/memory.py doctor . --write-checklist --write-state"}
        _log_tool_end("memory_init_refactor_bundle", status="missing", project_root=target_root, hotspot_index=hotspot_index)
        return json.dumps(payload, ensure_ascii=False, indent=2)
    except (IndexError, ValueError) as exc:
        payload = {"status": "invalid", "project_root": str(target_root), "message": str(exc), "hotspot_index": hotspot_index, "hotspot_token": hotspot_token or None}
        _log_tool_end("memory_init_refactor_bundle", status="invalid", project_root=target_root, hotspot_index=hotspot_index, hotspot_token=hotspot_token or None)
        return json.dumps(payload, ensure_ascii=False, indent=2)
    payload = _init_refactor_bundle_payload(ctx, target_root, result, dry_run)
    _log_tool_end(
        "memory_init_refactor_bundle",
        status="ok",
        project_root=target_root,
        hotspot_index=result.hotspot_index,
        hotspot_token=result.hotspot_token,
        task_slug=result.task_slug,
        dry_run=dry_run,
    )
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _filter_rules_by_domain(content: str, headers: list[str]) -> str:
    # Extract lines belonging to the first matching domain section.
    result_lines: list[str] = []
    in_section = False
    for line in content.splitlines():
        if any(line.startswith(h) for h in headers):
            in_section = True
        elif line.startswith("## ") and in_section:
            break
        if in_section:
            result_lines.append(line)
    return "\n".join(result_lines)


@mcp.tool()
def memory_get_rules(domain: str = "") -> str:
    # Return rule content filtered by domain, or all rules if no domain specified.
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
    result = _filter_rules_by_domain(content, headers)
    _log_tool_end("memory_get_rules", status="ok", scope=domain)
    return result or f"No rules found for domain: {domain}"


def _collect_keyword_matches(errors_dir: Path, keyword: str, limit: int) -> list[dict]:
    # Scan error records for the keyword and return matching metadata dicts.
    matches: list[dict] = []
    for filepath in sorted(errors_dir.glob("*.md")):
        content = filepath.read_text(encoding="utf-8").lower()
        if keyword in content:
            meta = parse_frontmatter(filepath)
            if meta:
                matches.append(meta)
        if len(matches) >= limit:
            break
    return matches


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


def _build_error_record_id(ctx: AppContext, project: str, today: str) -> tuple[str, Path]:
    existing = list(ctx.errors_dir.glob(f"{today}-{project}-*.md"))
    seq = str(len(existing) + 1).zfill(3)
    record_id = f"{today}-{project}-{seq}"
    return record_id, ctx.errors_dir / f"{record_id}.md"


def _build_error_content(
    record_id: str, today: str, *, project: str, domain: str, category: str, severity: str,
    task: str, error_desc: str, root_cause: str, fix: str, rule: str, file_path: str, tags: str,
) -> str:
    tag_items = [item.strip() for item in tags.split(",") if item.strip()]
    file_section = file_path if file_path else "<!-- 填写文件路径 -->"
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


@mcp.tool()
def memory_record_error(project: str, domain: str, category: str, severity: str, task: str, error_desc: str, root_cause: str, fix: str, rule: str, file_path: str = "", tags: str = "") -> str:
    # Validate params, build error record, write to disk, and update index.
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
    record_id, filename = _build_error_record_id(ctx, project, today)
    content = _build_error_content(record_id, today, project=project, domain=domain, category=category, severity=severity, task=task, error_desc=error_desc, root_cause=root_cause, fix=fix, rule=rule, file_path=file_path, tags=tags)
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


@mcp.tool()
def memory_wiki_list() -> str:
    """List all wiki topic names stored in memory/wiki/."""
    _log_tool_start("memory_wiki_list")
    topics = list_wiki_topics(ctx.wiki_dir)
    if not topics:
        _log_tool_end("memory_wiki_list", status="empty")
        return "Wiki is empty. Run amem wiki-ingest <path> to import documents."
    _log_tool_end("memory_wiki_list", status="ok", count=len(topics))
    return f"Wiki topics ({len(topics)}):\n" + "\n".join(f"• {t}" for t in topics)


@mcp.tool()
def memory_wiki_query(query: str, limit: int = 5) -> str:
    """Search wiki pages by keyword and return matching excerpts.

    Call this before starting a task to retrieve relevant rules and context.
    The output can be injected directly as a system-prompt prefix.
    """
    _log_tool_start("memory_wiki_query", query=query, limit=limit)
    matches = search_wiki(ctx.wiki_dir, query, limit=limit)
    if not matches:
        _log_tool_end("memory_wiki_query", status="no_matches", query=query)
        return f"No wiki pages matching '{query}'. Use memory_wiki_update to add knowledge."
    lines = [f"Wiki results for '{query}' ({len(matches)} page(s)):\n"]
    for match in matches:
        lines.append(f"=== [{match['topic']}] ===")
        lines.append(match["excerpt"])
        lines.append("")
    _log_tool_end("memory_wiki_query", status="ok", query=query, matches=len(matches))
    return "\n".join(lines)


@mcp.tool()
def memory_wiki_update(topic: str, content: str, source: str = "") -> str:
    """Create or update a wiki page for *topic* with *content*.

    Call this after completing a task to capture learnings, refined rules,
    or error patterns so they are available for future queries.

    Args:
        topic:   Short hyphen-separated identifier (e.g. 'python', 'error-patterns').
        content: Markdown body (or full page with frontmatter).
        source:  Optional description of where this knowledge came from.
    """
    _log_tool_start("memory_wiki_update", topic=topic, source=source or "")
    path = write_wiki_page(ctx.wiki_dir, topic, content, source=source)
    log_file_update(ctx.logger, action="wiki_update", path=path, detail=f"topic={topic}")
    _log_tool_end("memory_wiki_update", status="ok", topic=topic)
    return f"✅ Wiki page updated: {path}\nTopic: {topic}"


@mcp.tool()
def memory_wiki_compile(
    topic: str,
    scope: str = "errors",
    recent_n: int = 20,
    dry_run: bool = False,
) -> str:
    """Synthesise a wiki page's compiled_truth from recent error records using an LLM.

    Reads up to *recent_n* error records relevant to *topic*, calls the configured
    LLM (AMEM_LLM_PROVIDER / AMEM_LLM_MODEL env vars), updates the compiled_truth
    section of the wiki page, and appends a timeline entry.

    Use ``dry_run=True`` to preview without writing.

    Args:
        topic:     Wiki topic to compile (must already exist or will be created).
        scope:     Source scope — "errors" (default) or "all".
        recent_n:  Maximum number of error records to include in synthesis.
        dry_run:   If True, return a preview without writing to disk.
    """
    import json as _json
    _log_tool_start("memory_wiki_compile", topic=topic, scope=scope, recent_n=recent_n, dry_run=dry_run)
    try:
        result = compile_wiki_topic(
            ctx,
            topic,
            recent_n=recent_n,
            scope=scope,
            dry_run=dry_run,
        )
    except RuntimeError as exc:
        _log_tool_end("memory_wiki_compile", status="error", topic=topic)
        return f"❌ LLM 调用失败: {exc}"
    _log_tool_end("memory_wiki_compile", status=result["status"], topic=topic, error_count=result["error_count"])
    return _json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def memory_wiki_lint(check: str = "all") -> str:
    """Lint all wiki pages for structural issues.

    Checks for missing frontmatter fields, broken cross-links, and missing
    compiled_truth sections.

    Args:
        check: Scope of lint checks. Currently only "all" is supported.
    """
    import io as _io
    import contextlib as _contextlib
    from agents_memory.services.wiki import cmd_wiki_lint

    _log_tool_start("memory_wiki_lint", check=check)
    buf = _io.StringIO()
    with _contextlib.redirect_stdout(buf):
        exit_code = cmd_wiki_lint(ctx, [f"--check={check}"] if check != "all" else [])
    output = buf.getvalue()
    _log_tool_end("memory_wiki_lint", status="ok" if exit_code == 0 else "warnings")
    return output or "✅ Wiki lint 通过：未发现问题。"


@mcp.tool()
def memory_search(query: str, limit: int = 10, mode: str = "hybrid") -> str:
    """Search error records using hybrid FTS + vector ranking.

    Automatically rebuilds the FTS index when stale.
    Falls back gracefully when vector index is unavailable.

    Args:
        query: Natural-language or keyword search query.
        limit: Maximum number of results to return (default 10).
        mode:  "hybrid" (FTS+vector, default), "fts" (text only), "vector" (semantic only).
    """
    import json as _json
    from agents_memory.services.search import hybrid_search, search_fts
    from agents_memory.services.vector import cmd_vsearch

    _log_tool_start("memory_search", query=query, limit=limit, mode=mode)
    try:
        if mode == "fts":
            results = search_fts(ctx, query, limit=limit)
        elif mode == "vector":
            import io as _io
            import contextlib as _contextlib
            buf = _io.StringIO()
            with _contextlib.redirect_stdout(buf):
                cmd_vsearch(ctx, query, top_k=limit)
            _log_tool_end("memory_search", status="ok", mode=mode)
            return buf.getvalue()
        else:
            results = hybrid_search(ctx, query, limit=limit)
    except Exception as exc:  # noqa: BLE001
        _log_tool_end("memory_search", status="error")
        return f"❌ 搜索失败: {exc}"

    _log_tool_end("memory_search", status="ok", mode=mode, result_count=len(results))
    if not results:
        return f"未找到匹配 '{query}' 的记录。\n提示: 先运行 amem fts-index 或 amem embed 构建索引。"
    return _json.dumps(results, ensure_ascii=False, indent=2)


@mcp.tool()
def memory_ingest(
    content: str,
    source_type: str,
    source_ref: str = "",
    project: str = "",
    dry_run: bool = False,
) -> str:
    """Ingest a document (PR, meeting notes, decision, code review) into the memory system.

    Extracts insights via LLM, updates relevant wiki pages, appends timeline entries,
    and logs the event to memory/ingest_log.jsonl.

    Args:
        content:     Full text of the document to ingest.
        source_type: One of: pr-review, meeting, decision, code-review.
        source_ref:  Human-readable reference (e.g. "PR #123", "meeting 2024-01-15").
        project:     Optional project tag to associate with this ingest event.
        dry_run:     If True, preview without writing to disk.
    """
    import json as _json
    import tempfile
    import os
    from agents_memory.services.ingest import ingest_document, INGEST_TYPES

    if source_type not in INGEST_TYPES:
        return f"❌ 不支持的类型 '{source_type}'。支持: {', '.join(INGEST_TYPES)}"

    _log_tool_start("memory_ingest", source_type=source_type, source_ref=source_ref, project=project, dry_run=dry_run)

    # Write content to a temp file so ingest_document can read it
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = ingest_document(
            ctx,
            source_path=tmp_path,
            ingest_type=source_type,
            project=project,
            dry_run=dry_run,
        )
    finally:
        os.unlink(tmp_path)

    _log_tool_end("memory_ingest", status="ok" if not result.error else "error",
                  source_type=source_type, topics=len(result.topics_updated))

    if result.error:
        return f"❌ 摄取失败: {result.error}"

    prefix = "[DRY-RUN] " if dry_run else ""
    summary = {
        "status": "dry_run" if dry_run else "ok",
        "source_type": result.ingest_type,
        "source_ref": source_ref,
        "project": result.project,
        "summary": result.summary,
        "topics_updated": result.topics_updated,
        "timeline_entries_added": result.timeline_entries_added,
    }
    return f"{prefix}✅ 摄取完成\n\n" + _json.dumps(summary, ensure_ascii=False, indent=2)


def main() -> None:
    mcp.run()
