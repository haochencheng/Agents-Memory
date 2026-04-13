from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from agents_memory.runtime import AppContext
from agents_memory.services.planning_core import slugify_task_name
from agents_memory.services.projects import detect_project_id
from agents_memory.services.workflow_records import normalize_project_id
from agents_memory.services.wiki import get_wiki_links, list_wiki_topics, read_wiki_page, set_wiki_links, write_wiki_page


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

_DOC_TYPE_BY_SECTION = {
    "architecture": "architecture",
    "guides": "guide",
    "ops": "ops",
    "plans": "plan",
    "frontend": "frontend",
    "product": "product",
    "maintenance": "maintenance",
}

_TAG_STOPWORDS = {
    "docs",
    "doc",
    "readme",
    "agents",
    "design",
    "plan",
    "spec",
    "task",
    "validation",
    "overview",
    "guide",
    "architecture",
    "product",
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


def _parse_frontmatter(raw: str) -> dict[str, object]:
    meta: dict[str, object] = {}
    in_frontmatter = False
    for line in raw.splitlines():
        stripped = line.rstrip()
        if stripped == "---":
            if not in_frontmatter:
                in_frontmatter = True
                continue
            break
        if in_frontmatter and ": " in stripped:
            key, value = stripped.split(": ", 1)
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                inner = value[1:-1]
                meta[key.strip()] = [item.strip() for item in inner.split(",") if item.strip()]
            else:
                meta[key.strip()] = value.strip('"')
    return meta


def _doc_type_for_source(relative_path: str) -> str:
    parts = [part for part in Path(relative_path).parts if part]
    if not parts:
        return "reference"
    filename = parts[-1].lower()
    if len(parts) == 1:
        if filename == "architecture.md":
            return "architecture"
        if filename in {"bugs.md", "bugfix.md"} or filename.startswith("bug-"):
            return "maintenance"
        return "root-doc"
    if parts[0] == "docs":
        if len(parts) == 2:
            return "docs-root"
        return _DOC_TYPE_BY_SECTION.get(parts[1], parts[1].replace("_", "-"))
    return "reference"


def _tokenize_source(relative_path: str) -> list[str]:
    tokens = [
        token
        for token in re.findall(r"[a-z0-9]+", Path(relative_path).as_posix().lower())
        if len(token) >= 3 and token not in _TAG_STOPWORDS
    ]
    seen: set[str] = set()
    ordered: list[str] = []
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


def _tags_for_source(project_id: str, relative_path: str, *, doc_type: str) -> list[str]:
    tags: list[str] = []
    project_tokens = [token for token in project_id.split("-") if token]
    for token in _tokenize_source(relative_path):
        if token in project_tokens:
            continue
        tags.append(token)
    if doc_type not in {"reference", "root-doc", "docs-root"}:
        tags.insert(0, doc_type)
    tags.insert(0, project_id)
    deduped: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        if not tag or tag in seen:
            continue
        seen.add(tag)
        deduped.append(tag)
    return deduped[:8]


def _candidate_reason(shared_tags: list[str], same_doc_type: bool, same_section: bool) -> str:
    reasons: list[str] = []
    if shared_tags:
        reasons.append(f"共享标签: {', '.join(shared_tags[:3])}")
    if same_doc_type:
        reasons.append("同类文档")
    if same_section:
        reasons.append("同目录域")
    return "；".join(reasons) or "自动推断候选关系"


def _resolve_explicit_reference(current_source_path: str, target: str) -> str:
    cleaned = str(target).strip()
    if not cleaned or cleaned.startswith(("http://", "https://", "#", "mailto:")):
        return ""
    cleaned = cleaned.split("#", 1)[0].split("?", 1)[0].strip()
    if not cleaned.endswith(".md"):
        return ""
    candidate = Path(cleaned)
    resolved = candidate if candidate.is_absolute() else Path(current_source_path).parent / candidate
    normalized_parts: list[str] = []
    for part in resolved.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if normalized_parts:
                normalized_parts.pop()
            continue
        normalized_parts.append(part)
    return "/".join(normalized_parts)


def _explicit_reference_targets(raw: str, source_path: str) -> set[str]:
    targets: set[str] = set()
    for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", raw):
        resolved = _resolve_explicit_reference(source_path, match.group(1))
        if resolved:
            targets.add(resolved)
    for match in re.finditer(r"(?:(?:\.\./|\.?/)?(?:docs/)?[A-Za-z0-9._/-]+\.md)\b", raw):
        resolved = _resolve_explicit_reference(source_path, match.group(0))
        if resolved:
            targets.add(resolved)
    return targets


def _candidate_links(
    *,
    topic: str,
    project_id: str,
    source_path: str,
    doc_type: str,
    tags: list[str],
    raw: str,
    known_pages: list[dict[str, object]],
) -> list[dict[str, str]]:
    current_parts = tuple(Path(source_path).parts)
    explicit_targets = _explicit_reference_targets(raw, source_path)
    candidates: list[tuple[float, dict[str, str]]] = []
    for page in known_pages:
        other_topic = str(page.get("topic", "")).strip()
        if not other_topic or other_topic == topic:
            continue
        if normalize_project_id(str(page.get("project", ""))) != project_id:
            continue
        other_tags = [str(tag) for tag in page.get("tags", []) if str(tag)]
        shared_tags = sorted(set(tags) & set(other_tags) - {project_id})
        other_doc_type = str(page.get("doc_type", "")).strip()
        other_source_path = str(page.get("source_path", "")).strip()
        same_doc_type = bool(doc_type and other_doc_type and doc_type == other_doc_type)
        same_section = bool(current_parts and other_source_path and Path(other_source_path).parts[:2] == current_parts[:2])
        explicit_reference = bool(other_source_path and other_source_path in explicit_targets)
        score = 0.0
        context = _candidate_reason(shared_tags, same_doc_type, same_section)
        if explicit_reference:
            score += 3.2
            context = f"正文引用: {other_source_path}"
        if shared_tags:
            score += min(len(shared_tags), 3) * 1.4
        if same_doc_type:
            score += 0.6
        if same_section:
            score += 0.5
        if score < 1.4:
            continue
        candidates.append(
            (
                score,
                {
                    "topic": other_topic,
                    "context": context,
                },
            )
        )

    candidates.sort(key=lambda item: (-item[0], item[1]["topic"]))
    return [link for _, link in candidates[:4]]


def _current_wiki_pages(ctx: AppContext) -> list[dict[str, object]]:
    pages: list[dict[str, object]] = []
    for topic in list_wiki_topics(ctx.wiki_dir):
        raw = read_wiki_page(ctx.wiki_dir, topic)
        if raw is None:
            continue
        fm = _parse_frontmatter(raw)
        pages.append(
            {
                "topic": topic,
                "project": normalize_project_id(str(fm.get("project", ""))),
                "source_path": str(fm.get("source_path", "")),
                "doc_type": str(fm.get("doc_type", "")) or _doc_type_for_source(str(fm.get("source_path", ""))),
                "tags": [str(tag) for tag in fm.get("tags", []) if str(tag)],
                "links": get_wiki_links(raw),
                "raw": raw,
            }
        )
    return pages


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
    known_pages = _current_wiki_pages(ctx)

    for source_path in selected_paths:
        relative_path = source_path.relative_to(project_root).as_posix()
        content = source_path.read_text(encoding="utf-8")
        topic = _topic_for_source(resolved_project_id, project_root, source_path)
        doc_type = _doc_type_for_source(relative_path)
        tags = _tags_for_source(resolved_project_id, relative_path, doc_type=doc_type)
        links = _candidate_links(
            topic=topic,
            project_id=resolved_project_id,
            source_path=relative_path,
            doc_type=doc_type,
            tags=tags,
            raw=content,
            known_pages=known_pages,
        )
        sources.append(ProjectKnowledgeSource(source_path=relative_path, topic=topic))
        if dry_run:
            known_pages.append(
                {
                    "topic": topic,
                    "project": resolved_project_id,
                    "source_path": relative_path,
                    "doc_type": doc_type,
                    "tags": tags,
                    "links": links,
                    "raw": content,
                }
            )
            continue
        write_wiki_page(
            ctx.wiki_dir,
            topic,
            content,
            source=relative_path,
            frontmatter_extra={
                "project": resolved_project_id,
                "source_path": relative_path,
                "doc_type": doc_type,
                "tags": tags,
            },
        )
        if links:
            set_wiki_links(ctx.wiki_dir, topic, links)
        _append_project_ingest_log(ctx, project_id=resolved_project_id, topic=topic, source_path=relative_path)
        known_pages.append(
            {
                "topic": topic,
                "project": resolved_project_id,
                "source_path": relative_path,
                "doc_type": doc_type,
                "tags": tags,
                "links": links,
                "raw": content,
            }
        )

    ingested_count = 0 if dry_run else len(sources)
    return ProjectKnowledgeIngestResult(
        project_id=resolved_project_id,
        project_root=project_root,
        discovered_files=discovered_files,
        sources=sources,
        ingested_count=ingested_count,
        dry_run=dry_run,
    )
