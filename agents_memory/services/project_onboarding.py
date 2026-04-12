from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from agents_memory.runtime import AppContext
from agents_memory.services.planning_core import slugify_task_name
from agents_memory.services.projects import detect_project_id
from agents_memory.services.workflow_records import normalize_project_id
from agents_memory.services.wiki import write_wiki_page


_IGNORED_PARTS = {
    ".agents-memory",
    ".git",
    ".pytest_cache",
    ".venv",
    ".vscode",
    "build",
    "coverage",
    "dist",
    "logs",
    "memory",
    "node_modules",
    "playwright-report",
    "site-packages",
    "venv",
}

_IGNORED_RELATIVE_PREFIXES = (
    ".github/instructions/agents-memory",
)

_ROOT_KNOWLEDGE_FILES = (
    "README.md",
    "AGENTS.md",
    "DESIGN.md",
    "CONTRIBUTING.md",
)

_PRIORITY_FILES = {
    "readme.md": 0,
    "agents.md": 1,
    "design.md": 2,
    "contributing.md": 3,
    "docs/readme.md": 4,
}


@dataclass(frozen=True)
class ProjectKnowledgeSource:
    source_path: str
    topic: str


@dataclass(frozen=True)
class ProjectKnowledgeIngestResult:
    project_id: str
    project_root: Path
    discovered_files: list[str]
    sources: list[ProjectKnowledgeSource]
    ingested_count: int
    dry_run: bool


def _should_skip_path(path: Path, project_root: Path) -> bool:
    rel = path.relative_to(project_root).as_posix()
    if any(part in _IGNORED_PARTS for part in path.parts):
        return True
    return any(rel.startswith(prefix) for prefix in _IGNORED_RELATIVE_PREFIXES)


def _priority_key(path: Path, project_root: Path) -> tuple[int, int, str]:
    rel = path.relative_to(project_root).as_posix().lower()
    priority = _PRIORITY_FILES.get(rel, _PRIORITY_FILES.get(path.name.lower(), 10))
    return priority, len(path.relative_to(project_root).parts), rel


def _limit_sources(paths: list[Path], *, max_files: int | None) -> list[Path]:
    if max_files is None or max_files <= 0:
        return paths
    return paths[:max_files]


def _discover_docs_corpus(project_root: Path) -> list[Path]:
    docs_root = project_root / "docs"
    if not docs_root.exists() or not docs_root.is_dir():
        return []

    selected: list[Path] = []
    seen: set[Path] = set()

    for relative_name in _ROOT_KNOWLEDGE_FILES:
        candidate = project_root / relative_name
        if not candidate.exists() or not candidate.is_file():
            continue
        if candidate.suffix.lower() != ".md":
            continue
        if _should_skip_path(candidate, project_root):
            continue
        selected.append(candidate)
        seen.add(candidate)

    docs_candidates: list[Path] = []
    for path in docs_root.rglob("*.md"):
        if not path.is_file():
            continue
        if _should_skip_path(path, project_root):
            continue
        docs_candidates.append(path)

    for path in sorted(docs_candidates, key=lambda item: _priority_key(item, project_root)):
        if path in seen:
            continue
        selected.append(path)
        seen.add(path)

    return selected


def discover_project_wiki_sources(project_root: Path, *, max_files: int | None = None) -> list[Path]:
    preferred_docs = _discover_docs_corpus(project_root)
    if preferred_docs:
        return _limit_sources(preferred_docs, max_files=max_files)

    candidates: list[Path] = []
    for path in project_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() != ".md":
            continue
        if _should_skip_path(path, project_root):
            continue
        candidates.append(path)
    ordered = sorted(candidates, key=lambda item: _priority_key(item, project_root))
    return _limit_sources(ordered, max_files=max_files)


def _topic_for_source(project_id: str, project_root: Path, source_path: Path) -> str:
    rel = source_path.relative_to(project_root)
    stem = rel.as_posix().rsplit(".", 1)[0].replace("/", "-")
    return slugify_task_name(f"{project_id}-{stem}")


def _append_project_ingest_log(ctx: AppContext, *, project_id: str, topic: str, source_path: str) -> None:
    log_path = ctx.memory_dir / "ingest_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "source_type": "project_wiki",
        "project": project_id,
        "id": topic,
        "status": "ok",
        "source_path": source_path,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def ingest_project_wiki_sources(
    ctx: AppContext,
    project_root: Path,
    *,
    project_id: str | None = None,
    max_files: int | None = None,
    dry_run: bool = False,
    source_paths: list[Path] | None = None,
) -> ProjectKnowledgeIngestResult:
    resolved_project_id = normalize_project_id(project_id or detect_project_id(project_root))
    selected_paths = source_paths or discover_project_wiki_sources(project_root, max_files=max_files)
    discovered_files = [path.relative_to(project_root).as_posix() for path in selected_paths]
    sources: list[ProjectKnowledgeSource] = []

    for source_path in selected_paths:
        relative_path = source_path.relative_to(project_root).as_posix()
        topic = _topic_for_source(resolved_project_id, project_root, source_path)
        sources.append(ProjectKnowledgeSource(source_path=relative_path, topic=topic))
        if dry_run:
            continue
        content = source_path.read_text(encoding="utf-8")
        write_wiki_page(
            ctx.wiki_dir,
            topic,
            content,
            source=relative_path,
            frontmatter_extra={
                "project": resolved_project_id,
                "source_path": relative_path,
            },
        )
        _append_project_ingest_log(ctx, project_id=resolved_project_id, topic=topic, source_path=relative_path)

    ingested_count = 0 if dry_run else len(sources)
    return ProjectKnowledgeIngestResult(
        project_id=resolved_project_id,
        project_root=project_root,
        discovered_files=discovered_files,
        sources=sources,
        ingested_count=ingested_count,
        dry_run=dry_run,
    )
