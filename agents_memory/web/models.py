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
    doc_type: str = ""
    word_count: int
    updated_at: str = ""
    project: str = ""
    source_path: str = ""


class ErrorMeta(BaseModel):
    id: str
    title: str = ""
    status: str = ""
    project: str = ""
    created_at: str = ""
    severity: str = ""
    tags: list[str] = Field(default_factory=list)


class SearchMatchedConcept(BaseModel):
    id: str
    title: str
    node_type: str = ""
    score: float = 0.0
    primary_topic: str = ""
    project: str = ""


class SearchResult(BaseModel):
    type: Literal["error", "wiki", "workflow"]
    id: str
    title: str
    snippet: str = ""
    score: float = 0.0
    rerank_boost: float = 0.0
    rerank_reasons: list[str] = Field(default_factory=list)
    matched_concepts: list[SearchMatchedConcept] = Field(default_factory=list)


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
    storage_kind: str = ""


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
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0
    query: str = ""


class WikiDetailResponse(BaseModel):
    topic: str
    title: str
    tags: list[str] = Field(default_factory=list)
    doc_type: str = ""
    updated_at: str = ""
    project: str = ""
    source_path: str = ""
    frontmatter: dict[str, Any]
    content_html: str
    raw: str
    word_count: int
    links: list["TopicRelation"] = Field(default_factory=list)
    backlinks: list["TopicRelation"] = Field(default_factory=list)
    related_topics: list["TopicRelation"] = Field(default_factory=list)


class WikiLintResponse(BaseModel):
    issues: list[LintIssue]
    total: int


class ErrorListResponse(BaseModel):
    errors: list[ErrorMeta]
    total: int
    page: int = 1
    page_size: int = 20
    total_pages: int = 0


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
    storage_kind: str = ""


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


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


class ProjectInfo(BaseModel):
    id: str
    name: str
    description: str = ""
    profile_path: str = ""
    health: str = "unknown"
    wiki_count: int = 0
    error_count: int = 0
    workflow_count: int = 0
    rule_count: int = 0
    last_ingest: str = ""


class ProjectsResponse(BaseModel):
    projects: list[ProjectInfo]


class ProjectStatsResponse(BaseModel):
    id: str
    health: str = "unknown"
    wiki_count: int = 0
    error_count: int = 0
    workflow_count: int = 0
    checklist_done: int = 0
    ingest_count: int = 0
    last_error: str = ""
    last_ingest: str = ""


class WorkflowRecordMeta(BaseModel):
    id: str
    title: str = ""
    source_type: str = ""
    project: str = ""
    status: str = ""
    created_at: str = ""
    storage_kind: str = ""


class WorkflowListResponse(BaseModel):
    records: list[WorkflowRecordMeta]
    total: int = 0


class WorkflowDetailResponse(BaseModel):
    id: str
    title: str = ""
    source_type: str = ""
    project: str = ""
    status: str = ""
    created_at: str = ""
    storage_kind: str = ""
    content_html: str
    raw: str


class ProjectWikiNavItem(BaseModel):
    topic: str
    title: str
    tags: list[str] = Field(default_factory=list)
    project: str = ""
    source_path: str = ""
    nav_path: str = ""
    source_group: str = ""
    document_role: str = "reference"
    updated_at: str = ""
    word_count: int = 0


class ProjectWikiNavGroup(BaseModel):
    key: str
    label: str
    item_count: int = 0
    topics: list[ProjectWikiNavItem] = Field(default_factory=list)


class ProjectWikiNavNode(BaseModel):
    key: str
    label: str
    path: str
    depth: int = 0
    item_count: int = 0
    topics: list[ProjectWikiNavItem] = Field(default_factory=list)
    children: list["ProjectWikiNavNode"] = Field(default_factory=list)


class ProjectWikiNavResponse(BaseModel):
    project_id: str
    total_topics: int = 0
    items: list[ProjectWikiNavItem] = Field(default_factory=list)
    tree: list[ProjectWikiNavNode] = Field(default_factory=list)
    groups: list[ProjectWikiNavGroup] = Field(default_factory=list)


class ProjectOnboardingRequest(BaseModel):
    project_root: str
    full: bool = True
    ingest_wiki: bool = True
    max_files: int | None = Field(default=None, ge=1)
    dry_run: bool = False


class ProjectKnowledgeSourceResponse(BaseModel):
    source_path: str
    topic: str


class ProjectOnboardingResponse(BaseModel):
    success: bool
    project_id: str
    project_root: str
    full: bool
    ingest_wiki: bool
    dry_run: bool
    enable_exit_code: int
    enable_log: str = ""
    discovered_files: list[str] = Field(default_factory=list)
    ingested_files: int = 0
    wiki_topics: list[str] = Field(default_factory=list)
    sources: list[ProjectKnowledgeSourceResponse] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


class SchedulerTask(BaseModel):
    id: str
    name: str
    check_type: str = "docs"
    project: str = ""
    cron_expr: str = ""
    status: str = "active"
    last_run: str = ""
    next_run: str = ""
    last_result: str = ""


class SchedulerTaskCreate(BaseModel):
    name: str
    check_type: str = "docs"
    project: str = ""
    cron_expr: str = ""


class SchedulerTasksResponse(BaseModel):
    tasks: list[SchedulerTask]


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


class CheckResult(BaseModel):
    id: str
    project: str = ""
    check_type: str = "docs"
    status: str = "pass"
    run_at: str = ""
    summary: str = ""
    details: list[str] = Field(default_factory=list)


class ChecksResponse(BaseModel):
    checks: list[CheckResult]
    total: int


class ChecksSummary(BaseModel):
    docs_pass: int = 0
    docs_warn: int = 0
    docs_fail: int = 0
    profile_pass: int = 0
    profile_warn: int = 0
    profile_fail: int = 0
    plan_pass: int = 0
    plan_warn: int = 0
    plan_fail: int = 0


# ---------------------------------------------------------------------------
# Wiki Graph
# ---------------------------------------------------------------------------


class GraphNode(BaseModel):
    id: str
    title: str = ""
    node_type: str = "entity"
    project: str = ""
    word_count: int = 0
    tags: list[str] = Field(default_factory=list)
    primary_topic: str = ""
    topic_count: int = 1


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str = "reference"
    weight: float = 1.0


class TopicRelation(BaseModel):
    topic: str
    title: str = ""
    relation: str = "related"
    reason: str = ""
    score: float = 0.0
    project: str = ""
    tags: list[str] = Field(default_factory=list)


class WikiGraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


ProjectWikiNavNode.model_rebuild()
WikiDetailResponse.model_rebuild()
