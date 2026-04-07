"""agents_memory/web/api.py — FastAPI REST API for Agents-Memory Web UI.

Start:
    uvicorn agents_memory.web.api:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from agents_memory.runtime import AppContext, build_context
from agents_memory.services.records import collect_errors, parse_frontmatter, read_body
from agents_memory.services.wiki import (
    list_wiki_topics,
    parse_wiki_sections,
    read_wiki_page,
    update_compiled_truth,
)
from agents_memory.web.models import (
    CompileResponse,
    ErrorDetailResponse,
    ErrorListResponse,
    ErrorMeta,
    IngestLogEntry,
    IngestLogResponse,
    IngestRequest,
    IngestResponse,
    LintIssue,
    RulesResponse,
    SearchResponse,
    SearchResult,
    StatsResponse,
    TaskStatus,
    TopicMeta,
    WikiDetailResponse,
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
        "http://localhost:5173",
        "http://localhost:8501",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8501",
    ],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# In-memory async task store {task_id: TaskStatus}
_task_store: dict[str, dict[str, Any]] = {}


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
    fence_count = 0
    for line in raw.splitlines():
        stripped = line.rstrip()
        if stripped == "---":
            fence_count += 1
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
    projects: list[str] = sorted({e.get("project", "") for e in errors if e.get("project")})
    return StatsResponse(
        wiki_count=len(wiki_topics),
        error_count=len(errors),
        ingest_count=len(ingest_log),
        projects=projects,
    )


# ---------------------------------------------------------------------------
# Routes — Wiki
# ---------------------------------------------------------------------------


@app.get("/api/wiki/lint", response_model=WikiLintResponse)
def wiki_lint() -> WikiLintResponse:
    ctx = _get_ctx()
    issues = _lint_wiki(ctx)
    return WikiLintResponse(issues=issues, total=len(issues))


@app.get("/api/wiki", response_model=WikiListResponse)
def list_wiki() -> WikiListResponse:
    ctx = _get_ctx()
    topics_result: list[TopicMeta] = []
    for topic in list_wiki_topics(ctx.wiki_dir):
        raw = read_wiki_page(ctx.wiki_dir, topic)
        if raw is None:
            continue
        fm = _parse_frontmatter_str(raw)
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

    asyncio.create_task(_run())
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


@app.get("/api/search", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1),
    mode: str = Query("hybrid"),
    limit: int = Query(10, ge=1, le=100),
) -> SearchResponse:
    ctx = _get_ctx()
    results: list[SearchResult] = []

    if mode in ("hybrid", "keyword"):
        try:
            from agents_memory.services.search import hybrid_search, search_fts  # noqa: PLC0415
            if mode == "hybrid":
                raw_results = hybrid_search(ctx, q, limit=limit)
            else:
                raw_results = search_fts(ctx, q, limit=limit)
            for r in raw_results:
                filepath = r.get("filepath", "")
                snippet = ""
                if filepath and Path(filepath).exists():
                    try:
                        body = read_body(Path(filepath))
                        # Find first matching line
                        for line in body.splitlines():
                            if q.lower() in line.lower():
                                snippet = line.strip()[:200]
                                break
                        if not snippet:
                            snippet = body[:200]
                    except Exception:
                        pass
                results.append(
                    SearchResult(
                        type="error",
                        id=r.get("id", ""),
                        title=r.get("id", r.get("category", "")),
                        snippet=snippet,
                        score=r.get("combined_score", r.get("fts_score", 0.0)),
                    )
                )
        except Exception:
            pass

    # Also search wiki pages (simple text match)
    if mode in ("hybrid", "keyword", "semantic"):
        for topic in list_wiki_topics(ctx.wiki_dir):
            raw = read_wiki_page(ctx.wiki_dir, topic)
            if raw is None:
                continue
            if q.lower() in raw.lower():
                fm = _parse_frontmatter_str(raw)
                title = fm.get("topic", topic).replace("-", " ").title()
                snippet = ""
                for line in raw.splitlines():
                    if q.lower() in line.lower():
                        snippet = line.strip()[:200]
                        break
                results.append(
                    SearchResult(
                        type="wiki",
                        id=topic,
                        title=title,
                        snippet=snippet,
                        score=0.5,
                    )
                )

    # Sort by score descending, cap at limit
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
