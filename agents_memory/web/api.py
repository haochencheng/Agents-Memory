"""agents_memory/web/api.py — FastAPI REST API for Agents-Memory Web UI.

Start:
    uvicorn agents_memory.web.api:app --reload --port 10100
"""

from __future__ import annotations

import asyncio
import json
import time
from contextlib import redirect_stdout
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from agents_memory.runtime import AppContext, build_context
from agents_memory.services.records import collect_errors, parse_frontmatter, read_body
from agents_memory.services.integration import cmd_enable as run_enable_command
from agents_memory.services.project_onboarding import ingest_project_wiki_sources
from agents_memory.services.projects import parse_projects, resolve_project_target
from agents_memory.services.wiki import (
    list_wiki_topics,
    parse_wiki_sections,
    read_wiki_page,
    update_compiled_truth,
)
from agents_memory.web.models import (
    CheckResult,
    ChecksResponse,
    ChecksSummary,
    CompileResponse,
    ErrorDetailResponse,
    ErrorListResponse,
    ErrorMeta,
    GraphEdge,
    GraphNode,
    IngestLogEntry,
    IngestLogResponse,
    IngestRequest,
    IngestResponse,
    LintIssue,
    ProjectInfo,
    ProjectKnowledgeSourceResponse,
    ProjectOnboardingRequest,
    ProjectOnboardingResponse,
    ProjectStatsResponse,
    ProjectsResponse,
    RulesResponse,
    SchedulerTask,
    SchedulerTaskCreate,
    SchedulerTasksResponse,
    SearchResponse,
    SearchResult,
    StatsResponse,
    TaskStatus,
    TopicMeta,
    WikiDetailResponse,
    WikiGraphResponse,
    WikiLintResponse,
    WikiListResponse,
    WikiUpdateRequest,
    WikiUpdateResponse,
)
from agents_memory.web.renderer import md_to_html

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(title="Agents-Memory API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:10000",
        "http://127.0.0.1:10000",
    ],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

import uuid

# In-memory async task store {task_id: TaskStatus}
_task_store: dict[str, dict[str, Any]] = {}
# In-memory scheduler tasks store
_scheduler_tasks: list[dict[str, Any]] = []


def _get_ctx() -> AppContext:
    """Return a fresh AppContext per request (cheap — just path resolution)."""
    return build_context(logger_name="agents_memory.web")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_frontmatter_str(raw: str) -> dict[str, Any]:
    """Extract frontmatter key-value pairs from raw wiki page content."""
    meta: dict[str, Any] = {}
    in_front = False
    for line in raw.splitlines():
        stripped = line.rstrip()
        if stripped == "---":
            if not in_front:
                in_front = True
                continue
            break
        if in_front and ": " in stripped:
            key, value = stripped.split(": ", 1)
            raw_val = value.strip().strip('"')
            # Parse bracket lists like [tag1, tag2]
            if raw_val.startswith("[") and raw_val.endswith("]"):
                inner = raw_val[1:-1]
                meta[key.strip()] = [x.strip() for x in inner.split(",") if x.strip()]
            else:
                meta[key.strip()] = raw_val
    return meta


def _word_count(text: str) -> int:
    return len(text.split())


def _ingest_log_path(ctx: AppContext) -> Path:
    return ctx.memory_dir / "ingest_log.jsonl"


def _read_ingest_log(ctx: AppContext, limit: int = 50) -> list[dict[str, Any]]:
    log_path = _ingest_log_path(ctx)
    if not log_path.exists():
        return []
    lines = log_path.read_text(encoding="utf-8").splitlines()
    entries = []
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
        if len(entries) >= limit:
            break
    return entries


def _load_wiki_topic_entries(ctx: AppContext) -> list[tuple[str, str, dict[str, Any]]]:
    entries: list[tuple[str, str, dict[str, Any]]] = []
    for topic in list_wiki_topics(ctx.wiki_dir):
        raw = read_wiki_page(ctx.wiki_dir, topic)
        if raw is None:
            continue
        entries.append((topic, raw, _parse_frontmatter_str(raw)))
    return entries


def _registered_project_ids(ctx: AppContext) -> list[str]:
    return [item.get("id", "") for item in parse_projects(ctx) if item.get("id")]


def _wiki_stats_by_project(ctx: AppContext) -> tuple[dict[str, int], dict[str, list[tuple[str, str, dict[str, Any]]]]]:
    counts: dict[str, int] = {}
    grouped: dict[str, list[tuple[str, str, dict[str, Any]]]] = {}
    for topic, raw, fm in _load_wiki_topic_entries(ctx):
        project_id = str(fm.get("project", "")).strip()
        if not project_id:
            continue
        counts[project_id] = counts.get(project_id, 0) + 1
        grouped.setdefault(project_id, []).append((topic, raw, fm))
    return counts, grouped


def _ingest_stats_by_project(ctx: AppContext) -> tuple[dict[str, int], dict[str, str]]:
    counts: dict[str, int] = {}
    latest: dict[str, str] = {}
    for entry in _read_ingest_log(ctx, limit=10000):
        project_id = str(entry.get("project", "")).strip()
        if not project_id:
            continue
        counts[project_id] = counts.get(project_id, 0) + 1
        ts = str(entry.get("ts", ""))
        if ts and ts > latest.get(project_id, ""):
            latest[project_id] = ts
    return counts, latest


def _error_stats_by_project(ctx: AppContext) -> tuple[dict[str, int], dict[str, str]]:
    counts: dict[str, int] = {}
    latest_error: dict[str, str] = {}
    for error in collect_errors(ctx):
        project_id = str(error.get("project", "")).strip()
        if not project_id:
            continue
        counts[project_id] = counts.get(project_id, 0) + 1
        latest_error[project_id] = str(error.get("id", latest_error.get(project_id, "")))
    return counts, latest_error


# ---------------------------------------------------------------------------
# Wiki lint (simple checks)
# ---------------------------------------------------------------------------

_REQUIRED_SECTIONS = ["compiled_truth"]


def _lint_wiki(ctx: AppContext) -> list[LintIssue]:
    issues: list[LintIssue] = []
    topics = list_wiki_topics(ctx.wiki_dir)
    for topic in topics:
        raw = read_wiki_page(ctx.wiki_dir, topic)
        if raw is None:
            continue
        fm = _parse_frontmatter_str(raw)
        if not fm:
            issues.append(LintIssue(topic=topic, level="error", message="Missing or invalid frontmatter"))
        sections = parse_wiki_sections(raw)
        if not sections.get("compiled_truth", "").strip():
            issues.append(LintIssue(topic=topic, level="warning", message="Empty compiled_truth section"))
        if "updated_at" not in fm:
            issues.append(LintIssue(topic=topic, level="warning", message="Missing updated_at in frontmatter"))
    return issues


# ---------------------------------------------------------------------------
# Routes — Stats
# ---------------------------------------------------------------------------


@app.get("/api/stats", response_model=StatsResponse)
def get_stats() -> StatsResponse:
    ctx = _get_ctx()
    wiki_topics = list_wiki_topics(ctx.wiki_dir)
    errors = collect_errors(ctx)
    ingest_log = _read_ingest_log(ctx, limit=10000)
    projects: set[str] = set(_registered_project_ids(ctx))
    projects.update(str(e.get("project", "")).strip() for e in errors if e.get("project"))
    projects.update(str(e.get("project", "")).strip() for e in ingest_log if e.get("project"))
    for _topic, _raw, fm in _load_wiki_topic_entries(ctx):
        project_id = str(fm.get("project", "")).strip()
        if project_id:
            projects.add(project_id)
    return StatsResponse(
        wiki_count=len(wiki_topics),
        error_count=len(errors),
        ingest_count=len(ingest_log),
        projects=sorted(project for project in projects if project),
    )


# ---------------------------------------------------------------------------
# Routes — Projects
# ---------------------------------------------------------------------------


@app.get("/api/projects", response_model=ProjectsResponse)
def list_projects() -> ProjectsResponse:
    ctx = _get_ctx()
    raw_projects = parse_projects(ctx)
    error_counts, _latest_error = _error_stats_by_project(ctx)
    wiki_counts, _grouped_wiki = _wiki_stats_by_project(ctx)
    _, latest_ingest = _ingest_stats_by_project(ctx)
    projects = [
        ProjectInfo(
            id=p.get("id", ""),
            name=p.get("id", ""),
            description=p.get("description", ""),
            health="ok" if error_counts.get(p.get("id", ""), 0) == 0 else "warn",
            wiki_count=wiki_counts.get(p.get("id", ""), 0),
            error_count=error_counts.get(p.get("id", ""), 0),
            last_ingest=latest_ingest.get(p.get("id", ""), ""),
        )
        for p in raw_projects
    ]
    return ProjectsResponse(projects=projects)


@app.get("/api/projects/{project_id}/stats", response_model=ProjectStatsResponse)
def project_stats(project_id: str) -> ProjectStatsResponse:
    ctx = _get_ctx()
    error_counts, latest_error = _error_stats_by_project(ctx)
    wiki_counts, _grouped_wiki = _wiki_stats_by_project(ctx)
    ingest_counts, latest_ingest = _ingest_stats_by_project(ctx)
    err_count = error_counts.get(project_id, 0)
    health = "ok" if err_count == 0 else "warn"
    return ProjectStatsResponse(
        id=project_id,
        health=health,
        wiki_count=wiki_counts.get(project_id, 0),
        error_count=err_count,
        checklist_done=0,
        ingest_count=ingest_counts.get(project_id, 0),
        last_error=latest_error.get(project_id, ""),
        last_ingest=latest_ingest.get(project_id, ""),
    )


# ---------------------------------------------------------------------------
# Routes — Scheduler
# ---------------------------------------------------------------------------


@app.get("/api/scheduler/tasks", response_model=SchedulerTasksResponse)
def list_scheduler_tasks() -> SchedulerTasksResponse:
    return SchedulerTasksResponse(tasks=[SchedulerTask(**t) for t in _scheduler_tasks])


@app.post("/api/scheduler/tasks", response_model=SchedulerTask, status_code=201)
def create_scheduler_task(body: SchedulerTaskCreate) -> SchedulerTask:
    task = SchedulerTask(
        id=str(uuid.uuid4())[:8],
        name=body.name,
        check_type=body.check_type,
        project=body.project,
        cron_expr=body.cron_expr,
        status="active",
    )
    _scheduler_tasks.append(task.model_dump())
    return task


@app.delete("/api/scheduler/tasks/{task_id}", status_code=204)
def delete_scheduler_task(task_id: str) -> None:
    global _scheduler_tasks
    before = len(_scheduler_tasks)
    _scheduler_tasks = [t for t in _scheduler_tasks if t.get("id") != task_id]
    if len(_scheduler_tasks) == before:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")


# ---------------------------------------------------------------------------
# Routes — Checks
# ---------------------------------------------------------------------------


@app.get("/api/checks", response_model=ChecksResponse)
def list_checks(
    project: str | None = Query(None),
    check_type: str | None = Query(None),
    status: str | None = Query(None),
) -> ChecksResponse:
    # Returns empty list — checks are populated by CLI runs
    return ChecksResponse(checks=[], total=0)


@app.get("/api/checks/summary", response_model=ChecksSummary)
def checks_summary() -> ChecksSummary:
    return ChecksSummary()


# ---------------------------------------------------------------------------
# Routes — Wiki
# ---------------------------------------------------------------------------


@app.get("/api/wiki/lint", response_model=WikiLintResponse)
def wiki_lint() -> WikiLintResponse:
    ctx = _get_ctx()
    issues = _lint_wiki(ctx)
    return WikiLintResponse(issues=issues, total=len(issues))


@app.get("/api/wiki/graph", response_model=WikiGraphResponse)
def wiki_graph() -> WikiGraphResponse:
    """Build a reference graph from wiki topics.
    
    Nodes = all wiki topics; edges = cross-references between pages.
    """
    ctx = _get_ctx()
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    topic_ids: set[str] = set()

    for topic in list_wiki_topics(ctx.wiki_dir):
        raw = read_wiki_page(ctx.wiki_dir, topic)
        if raw is None:
            continue
        fm = _parse_frontmatter_str(raw)
        title = fm.get("topic", topic).replace("-", " ").title()
        nodes.append(GraphNode(
            id=topic,
            title=title,
            project=str(fm.get("project", "")),
            word_count=_word_count(raw),
        ))
        topic_ids.add(topic)

    # Build edges from [[topic]] or [text](topic) links in wiki pages
    import re as _re
    for topic in topic_ids:
        raw = read_wiki_page(ctx.wiki_dir, topic)
        if raw is None:
            continue
        # Match markdown links and wiki-style [[links]]
        links = _re.findall(r"\[\[([^\]]+)\]\]|\[.+?\]\(([^)]+)\)", raw)
        for match in links:
            target = match[0] or match[1]
            # Normalise: strip extension, lowercase
            target = target.split("/")[-1].replace(".md", "").strip()
            if target and target in topic_ids and target != topic:
                edges.append(GraphEdge(source=topic, target=target))

    return WikiGraphResponse(nodes=nodes, edges=edges)


@app.get("/api/wiki", response_model=WikiListResponse)
def list_wiki() -> WikiListResponse:
    ctx = _get_ctx()
    topics_result: list[TopicMeta] = []
    for topic, raw, fm in _load_wiki_topic_entries(ctx):
        title = fm.get("topic", topic).replace("-", " ").title()
        tags = fm.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]
        topics_result.append(
            TopicMeta(
                topic=topic,
                title=title,
                tags=tags,
                word_count=_word_count(raw),
                updated_at=fm.get("updated_at", ""),
                project=str(fm.get("project", "")),
                source_path=str(fm.get("source_path", "")),
            )
        )
    return WikiListResponse(topics=topics_result)


@app.get("/api/wiki/{topic}", response_model=WikiDetailResponse)
def wiki_detail(topic: str) -> WikiDetailResponse:
    ctx = _get_ctx()
    raw = read_wiki_page(ctx.wiki_dir, topic)
    if raw is None:
        raise HTTPException(status_code=404, detail=f"Topic '{topic}' not found")
    fm = _parse_frontmatter_str(raw)
    title = fm.get("topic", topic).replace("-", " ").title()
    return WikiDetailResponse(
        topic=topic,
        title=title,
        frontmatter=fm,
        content_html=md_to_html(raw),
        raw=raw,
        word_count=_word_count(raw),
    )


@app.put("/api/wiki/{topic}", response_model=WikiUpdateResponse)
def wiki_update(topic: str, body: WikiUpdateRequest) -> WikiUpdateResponse:  # WRITE
    ctx = _get_ctx()
    existing = read_wiki_page(ctx.wiki_dir, topic)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Topic '{topic}' not found")
    update_compiled_truth(ctx.wiki_dir, topic, body.compiled_truth)
    return WikiUpdateResponse(topic=topic, updated=True)


@app.post("/api/wiki/{topic}/compile", response_model=CompileResponse, status_code=202)
async def wiki_compile(topic: str) -> CompileResponse:  # WRITE
    ctx = _get_ctx()
    existing = read_wiki_page(ctx.wiki_dir, topic)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Topic '{topic}' not found")
    task_id = f"compile-{topic}-{int(time.time())}"
    _task_store[task_id] = {"status": "pending", "started_at": time.time(), "result": {}}

    async def _run() -> None:
        _task_store[task_id]["status"] = "running"
        start = _task_store[task_id]["started_at"]
        try:
            from agents_memory.services.wiki_compile import compile_wiki_topic  # noqa: PLC0415
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, compile_wiki_topic, ctx, topic)
            _task_store[task_id].update(
                status="done",
                elapsed_s=round(time.time() - start, 2),
                result=result if isinstance(result, dict) else {"output": str(result)},
            )
        except Exception as exc:
            _task_store[task_id].update(
                status="failed",
                elapsed_s=round(time.time() - start, 2),
                result={"error": str(exc)},
            )

    task = asyncio.create_task(_run())
    _task_store[task_id]["task"] = task
    return CompileResponse(task_id=task_id, status="pending")


# ---------------------------------------------------------------------------
# Routes — Errors
# ---------------------------------------------------------------------------


@app.get("/api/errors", response_model=ErrorListResponse)
def list_errors(
    status: str | None = Query(None),
    project: str | None = Query(None),
    limit: int = Query(20, ge=1, le=500),
) -> ErrorListResponse:
    ctx = _get_ctx()
    status_filter = [status] if status else None
    records = collect_errors(ctx, status_filter=status_filter)
    if project:
        records = [r for r in records if r.get("project") == project]
    records = records[:limit]
    error_metas = [
        ErrorMeta(
            id=r.get("id", ""),
            title=r.get("title", r.get("id", "")),
            status=r.get("status", ""),
            project=r.get("project", ""),
            created_at=r.get("date", r.get("created_at", "")),
            severity=r.get("severity", ""),
        )
        for r in records
    ]
    return ErrorListResponse(errors=error_metas, total=len(error_metas))


@app.get("/api/errors/{error_id}", response_model=ErrorDetailResponse)
def error_detail(error_id: str) -> ErrorDetailResponse:
    ctx = _get_ctx()
    # Search through errors dir
    path = ctx.errors_dir / f"{error_id}.md"
    if not path.exists():
        # Try substring match
        matches = list(ctx.errors_dir.glob(f"*{error_id}*.md"))
        if not matches:
            raise HTTPException(status_code=404, detail=f"Error '{error_id}' not found")
        path = matches[0]
    raw = path.read_text(encoding="utf-8")
    fm = parse_frontmatter(path)
    body = read_body(path)
    return ErrorDetailResponse(
        id=fm.get("id", path.stem),
        title=fm.get("title", fm.get("id", path.stem)),
        status=fm.get("status", ""),
        project=fm.get("project", ""),
        content_html=md_to_html(body),
        raw=raw,
        created_at=fm.get("date", fm.get("created_at", "")),
    )


# ---------------------------------------------------------------------------
# Routes — Search
# ---------------------------------------------------------------------------


def _extract_snippet(filepath: str, q: str) -> str:
    """Return the first line matching q from filepath, or first 200 chars."""
    if not filepath or not Path(filepath).exists():
        return ""
    try:
        body = read_body(Path(filepath))
        matched = next((l.strip()[:200] for l in body.splitlines() if q.lower() in l.lower()), "")
        return matched or body[:200]
    except Exception:
        return ""


def _search_errors(ctx, q: str, mode: str, limit: int) -> list[SearchResult]:
    """Run FTS or hybrid search over error records and return SearchResult list.

    # Guard mode → import search → map raw rows to SearchResult via _extract_snippet.
    """
    if mode not in ("hybrid", "keyword"):
        return []
    try:
        from agents_memory.services.search import hybrid_search, search_fts  # noqa: PLC0415
        raw = hybrid_search(ctx, q, limit=limit) if mode == "hybrid" else search_fts(ctx, q, limit=limit)
        return [
            SearchResult(
                type="error",
                id=r.get("id", ""),
                title=r.get("id", r.get("category", "")),
                snippet=_extract_snippet(r.get("filepath", ""), q),
                score=r.get("combined_score", r.get("fts_score", 0.0)),
            )
            for r in raw
        ]
    except Exception:
        return []


def _search_wiki(ctx, q: str, mode: str) -> list[SearchResult]:
    """Simple text-match search over wiki pages; available in all modes."""
    results: list[SearchResult] = []
    if mode not in ("hybrid", "keyword", "semantic"):
        return results
    for topic in list_wiki_topics(ctx.wiki_dir):
        raw = read_wiki_page(ctx.wiki_dir, topic)
        if raw is None or q.lower() not in raw.lower():
            continue
        fm = _parse_frontmatter_str(raw)
        title = fm.get("topic", topic).replace("-", " ").title()
        snippet = next(
            (line.strip()[:200] for line in raw.splitlines() if q.lower() in line.lower()),
            "",
        )
        results.append(SearchResult(type="wiki", id=topic, title=title, snippet=snippet, score=0.5))
    return results


@app.get("/api/search", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1),
    mode: str = Query("hybrid"),
    limit: int = Query(10, ge=1, le=100),
) -> SearchResponse:
    """Unified search endpoint: merges error-record (FTS/hybrid) + wiki results.

    # Two sub-searches run in sequence: _search_errors (FTS/hybrid) then _search_wiki (text-match).
    """
    ctx = _get_ctx()
    results: list[SearchResult] = _search_errors(ctx, q, mode, limit)
    results += _search_wiki(ctx, q, mode)
    results.sort(key=lambda x: x.score, reverse=True)
    results = results[:limit]
    return SearchResponse(query=q, mode=mode, results=results, total=len(results))


# ---------------------------------------------------------------------------
# Routes — Ingest
# ---------------------------------------------------------------------------


@app.post("/api/ingest", response_model=IngestResponse, status_code=200)
def ingest(body: IngestRequest) -> IngestResponse:  # WRITE
    ctx = _get_ctx()
    if body.dry_run:
        return IngestResponse(ingested=False, id="", dry_run=True)

    # Write as error record if source_type == error_record
    from datetime import date  # noqa: PLC0415
    today = date.today().strftime("%Y%m%d")
    existing = list(ctx.errors_dir.glob(f"*{today}*.md"))
    seq = len(existing) + 1
    record_id = f"ERR-{today}-{seq:03d}"
    project_tag = body.project or "unknown"
    content = body.content
    if not content.lstrip().startswith("---"):
        fm = f"---\nid: {record_id}\nproject: {project_tag}\nsource_type: {body.source_type}\nstatus: new\ndate: {date.today().isoformat()}\n---\n\n"
        content = fm + content
    path = ctx.errors_dir / f"{record_id}.md"
    path.write_text(content, encoding="utf-8")

    # Append to ingest log
    log_path = _ingest_log_path(ctx)
    log_entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "source_type": body.source_type,
        "project": project_tag,
        "id": record_id,
        "status": "ok",
    }
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(log_entry) + "\n")

    return IngestResponse(ingested=True, id=record_id, dry_run=False)


@app.get("/api/ingest/log", response_model=IngestLogResponse)
def ingest_log(limit: int = Query(50, ge=1, le=1000)) -> IngestLogResponse:
    ctx = _get_ctx()
    entries_raw = _read_ingest_log(ctx, limit=limit)
    entries = [
        IngestLogEntry(
            ts=e.get("ts", ""),
            source_type=e.get("source_type", ""),
            project=e.get("project", ""),
            id=e.get("id", ""),
            status=e.get("status", ""),
        )
        for e in entries_raw
    ]
    return IngestLogResponse(entries=entries, total=len(entries))


@app.post("/api/onboarding/bootstrap", response_model=ProjectOnboardingResponse, status_code=200)
def onboarding_bootstrap(body: ProjectOnboardingRequest) -> ProjectOnboardingResponse:
    ctx = _get_ctx()
    project_root = Path(body.project_root).expanduser().resolve()
    if not project_root.exists() or not project_root.is_dir():
        raise HTTPException(status_code=404, detail=f"Project root '{project_root}' not found")

    enable_buffer = StringIO()
    with redirect_stdout(enable_buffer):
        enable_exit_code = run_enable_command(
            ctx,
            str(project_root),
            full=body.full,
            dry_run=body.dry_run,
            json_output=False,
        )

    project_id = resolve_project_target(ctx, str(project_root))[0]
    discovered_files: list[str] = []
    sources: list[ProjectKnowledgeSourceResponse] = []
    ingested_files = 0
    wiki_topics: list[str] = []

    if body.ingest_wiki and enable_exit_code == 0:
        ingest_result = ingest_project_wiki_sources(
            ctx,
            project_root,
            project_id=project_id,
            max_files=max(1, body.max_files),
            dry_run=body.dry_run,
        )
        discovered_files = ingest_result.discovered_files
        sources = [
            ProjectKnowledgeSourceResponse(source_path=item.source_path, topic=item.topic)
            for item in ingest_result.sources
        ]
        ingested_files = ingest_result.ingested_count
        wiki_topics = [item.topic for item in ingest_result.sources]

    return ProjectOnboardingResponse(
        success=enable_exit_code == 0,
        project_id=project_id,
        project_root=str(project_root),
        full=body.full,
        ingest_wiki=body.ingest_wiki,
        dry_run=body.dry_run,
        enable_exit_code=enable_exit_code,
        enable_log=enable_buffer.getvalue().strip(),
        discovered_files=discovered_files,
        ingested_files=ingested_files,
        wiki_topics=wiki_topics,
        sources=sources,
    )


# ---------------------------------------------------------------------------
# Routes — Rules
# ---------------------------------------------------------------------------


@app.get("/api/rules", response_model=RulesResponse)
def get_rules() -> RulesResponse:
    ctx = _get_ctx()
    if not ctx.rules_file.exists():
        return RulesResponse(content_html="<p>rules.md not found</p>", raw="", word_count=0)
    raw = ctx.rules_file.read_text(encoding="utf-8")
    return RulesResponse(
        content_html=md_to_html(raw),
        raw=raw,
        word_count=_word_count(raw),
    )


# ---------------------------------------------------------------------------
# Routes — Async Tasks
# ---------------------------------------------------------------------------


@app.get("/api/tasks/{task_id}", response_model=TaskStatus)
def task_status(task_id: str) -> TaskStatus:
    task = _task_store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    elapsed = round(time.time() - task.get("started_at", time.time()), 2)
    return TaskStatus(
        task_id=task_id,
        status=task.get("status", "pending"),
        elapsed_s=task.get("elapsed_s", elapsed),
        result=task.get("result", {}),
    )
