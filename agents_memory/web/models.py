"""agents_memory/web/models.py — Pydantic request/response schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------


class TopicMeta(BaseModel):
    topic: str
    title: str
    tags: list[str] = Field(default_factory=list)
    word_count: int
    updated_at: str = ""


class ErrorMeta(BaseModel):
    id: str
    title: str = ""
    status: str = ""
    project: str = ""
    created_at: str = ""
    severity: str = ""
    tags: list[str] = Field(default_factory=list)


class SearchResult(BaseModel):
    type: Literal["error", "wiki"]
    id: str
    title: str
    snippet: str = ""
    score: float = 0.0


class LintIssue(BaseModel):
    topic: str
    level: str = "warning"
    message: str


class TaskStatus(BaseModel):
    task_id: str
    status: Literal["pending", "running", "done", "failed"]
    elapsed_s: float = 0.0
    result: dict[str, Any] = Field(default_factory=dict)


class IngestLogEntry(BaseModel):
    ts: str
    source_type: str = ""
    project: str = ""
    id: str = ""
    status: str = ""


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class WikiUpdateRequest(BaseModel):
    compiled_truth: str


class IngestRequest(BaseModel):
    content: str
    source_type: str = "error_record"
    project: str = ""
    dry_run: bool = False


# ---------------------------------------------------------------------------
# Response envelopes
# ---------------------------------------------------------------------------


class StatsResponse(BaseModel):
    wiki_count: int
    error_count: int
    ingest_count: int
    projects: list[str] = Field(default_factory=list)


class WikiListResponse(BaseModel):
    topics: list[TopicMeta]


class WikiDetailResponse(BaseModel):
    topic: str
    title: str
    frontmatter: dict[str, Any]
    content_html: str
    raw: str
    word_count: int


class WikiLintResponse(BaseModel):
    issues: list[LintIssue]
    total: int


class ErrorListResponse(BaseModel):
    errors: list[ErrorMeta]
    total: int


class ErrorDetailResponse(BaseModel):
    id: str
    title: str = ""
    status: str = ""
    project: str = ""
    content_html: str
    raw: str
    created_at: str = ""


class SearchResponse(BaseModel):
    query: str
    mode: str
    results: list[SearchResult]
    total: int


class IngestResponse(BaseModel):
    ingested: bool
    id: str = ""
    dry_run: bool


class IngestLogResponse(BaseModel):
    entries: list[IngestLogEntry]
    total: int


class RulesResponse(BaseModel):
    content_html: str
    raw: str
    word_count: int


class WikiUpdateResponse(BaseModel):
    topic: str
    updated: bool


class CompileResponse(BaseModel):
    task_id: str
    status: str


class IngestStatusResponse(BaseModel):
    ingested: bool
    id: str = ""
    dry_run: bool
