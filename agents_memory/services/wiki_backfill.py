from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from agents_memory.runtime import AppContext
from agents_memory.services.project_onboarding import (
    _candidate_links,
    _doc_type_for_source,
    _parse_frontmatter,
    _tags_for_source,
)
from agents_memory.services.projects import parse_projects
from agents_memory.services.workflow_records import normalize_project_id
from agents_memory.services.wiki import get_wiki_links, list_wiki_topics, read_wiki_page, set_wiki_links, write_wiki_page


_ROOT_DOC_SOURCE_MAP = {
    "readme": "README.md",
    "agents": "AGENTS.md",
    "design": "DESIGN.md",
    "contributing": "CONTRIBUTING.md",
}

_DOC_SECTIONS = {
    "architecture",
    "guides",
    "ops",
    "plans",
    "frontend",
    "product",
    "maintenance",
}


@dataclass(frozen=True)
class WikiBackfillItem:
    topic: str
    project: str
    source_path: str
    doc_type: str
    changed_fields: list[str] = field(default_factory=list)
    added_links: list[str] = field(default_factory=list)
    updated: bool = False


@dataclass(frozen=True)
class WikiBackfillResult:
    updated: int
    skipped: int
    items: list[WikiBackfillItem] = field(default_factory=list)


def _known_project_ids(ctx: AppContext) -> list[str]:
    project_ids = [
        normalize_project_id(item.get("id", ""))
        for item in parse_projects(ctx)
        if item.get("id")
    ]
    current_repo = normalize_project_id(ctx.base_dir.name)
    if current_repo:
        project_ids.append(current_repo)
    deduped: list[str] = []
    seen: set[str] = set()
    for project_id in project_ids:
        if not project_id or project_id in seen:
            continue
        seen.add(project_id)
        deduped.append(project_id)
    return deduped


def infer_project_id_for_topic(topic: str, known_project_ids: list[str], *, prefix_counts: dict[str, int] | None = None) -> str:
    normalized_topic = normalize_project_id(topic)
    for project_id in sorted(known_project_ids, key=len, reverse=True):
        if normalized_topic == project_id or normalized_topic.startswith(f"{project_id}-"):
            return project_id
    parts = [part for part in normalized_topic.split("-") if part]
    if not parts:
        return ""
    if parts[-1] in _ROOT_DOC_SOURCE_MAP and len(parts) > 1:
        return "-".join(parts[:-1])
    if "docs" in parts:
        docs_index = parts.index("docs")
        if docs_index > 0:
            return "-".join(parts[:docs_index])
    if prefix_counts and parts:
        first_prefix = parts[0]
        if prefix_counts.get(first_prefix, 0) >= 3:
            return first_prefix
    return ""


def infer_source_path_for_topic(topic: str, project_id: str) -> str:
    remainder = topic
    if project_id and topic.startswith(f"{project_id}-"):
        remainder = topic[len(project_id) + 1 :]
    parts = [part for part in remainder.split("-") if part]
    if not parts:
        return ""
    if len(parts) == 1 and parts[0] in _ROOT_DOC_SOURCE_MAP:
        return _ROOT_DOC_SOURCE_MAP[parts[0]]
    if parts[0] == "docs":
        if len(parts) == 1:
            return "docs/README.md"
        if len(parts) >= 3 and parts[1] in _DOC_SECTIONS:
            return f"docs/{parts[1]}/{'-'.join(parts[2:])}.md"
        if len(parts) >= 3:
            return f"docs/{parts[1]}/{'-'.join(parts[2:])}.md"
        return f"docs/{'-'.join(parts[1:])}.md"
    return ""


def _dedupe_tags(existing_tags: list[str], inferred_tags: list[str]) -> list[str]:
    tags: list[str] = []
    seen: set[str] = set()
    for tag in [*existing_tags, *inferred_tags]:
        cleaned = str(tag).strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        tags.append(cleaned)
    return tags[:8]


def _frontmatter_source_path(frontmatter: dict[str, object]) -> str:
    explicit = str(frontmatter.get("source_path", "")).strip()
    if explicit:
        return explicit
    sources = frontmatter.get("sources", [])
    if isinstance(sources, list):
        for source in sources:
            cleaned = str(source).strip()
            if cleaned:
                return cleaned
    return ""


def _merge_links(existing_links: list[dict[str, str]], candidate_links: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[str]]:
    merged = [dict(link) for link in existing_links]
    existing_topics = {str(link.get("topic", "")).strip() for link in existing_links}
    added_topics: list[str] = []
    for link in candidate_links:
        topic = str(link.get("topic", "")).strip()
        if not topic or topic in existing_topics:
            continue
        existing_topics.add(topic)
        merged.append(dict(link))
        added_topics.append(topic)
    return merged, added_topics


def _planned_pages(ctx: AppContext) -> list[dict[str, object]]:
    known_project_ids = _known_project_ids(ctx)
    prefix_counts: dict[str, int] = {}
    for topic in list_wiki_topics(ctx.wiki_dir):
        first = normalize_project_id(topic).split("-", 1)[0]
        if first:
            prefix_counts[first] = prefix_counts.get(first, 0) + 1
    planned: list[dict[str, object]] = []
    for topic in list_wiki_topics(ctx.wiki_dir):
        raw = read_wiki_page(ctx.wiki_dir, topic)
        if raw is None:
            continue
        frontmatter = _parse_frontmatter(raw)
        project_id = normalize_project_id(str(frontmatter.get("project", ""))) or infer_project_id_for_topic(topic, known_project_ids, prefix_counts=prefix_counts)
        source_path = _frontmatter_source_path(frontmatter) or infer_source_path_for_topic(topic, project_id)
        if not project_id and source_path:
            project_id = normalize_project_id(ctx.base_dir.name)
        doc_type = str(frontmatter.get("doc_type", "")).strip() or _doc_type_for_source(source_path or topic)
        existing_tags = [str(tag) for tag in frontmatter.get("tags", []) if str(tag)]
        inferred_tags = _tags_for_source(project_id or "unknown", source_path or topic, doc_type=doc_type)
        planned.append(
            {
                "topic": topic,
                "raw": raw,
                "frontmatter": frontmatter,
                "project": project_id,
                "source_path": source_path,
                "doc_type": doc_type,
                "tags": _dedupe_tags(existing_tags, inferred_tags),
                "links": get_wiki_links(raw),
            }
        )
    return planned


def backfill_wiki_metadata_and_links(
    ctx: AppContext,
    *,
    dry_run: bool = False,
    limit: int | None = None,
    project: str | None = None,
) -> WikiBackfillResult:
    planned_pages = _planned_pages(ctx)
    normalized_project = normalize_project_id(project or "")
    items: list[WikiBackfillItem] = []
    updated = 0
    skipped = 0

    selected_pages = [
        page for page in planned_pages
        if not normalized_project or str(page.get("project", "")) == normalized_project
    ]
    if limit is not None and limit > 0:
        selected_pages = selected_pages[:limit]

    for page in selected_pages:
        topic = str(page["topic"])
        raw = str(page["raw"])
        frontmatter = dict(page["frontmatter"])
        project_id = str(page["project"])
        source_path = str(page["source_path"])
        doc_type = str(page["doc_type"])
        tags = [str(tag) for tag in page["tags"]]
        existing_links = [dict(link) for link in page["links"]]

        candidate_links = _candidate_links(
            topic=topic,
            project_id=project_id,
            source_path=source_path or topic,
            doc_type=doc_type,
            tags=tags,
            known_pages=planned_pages,
        )
        merged_links, added_links = _merge_links(existing_links, candidate_links)

        changed_fields: list[str] = []
        if project_id and normalize_project_id(str(frontmatter.get("project", ""))) != project_id:
            changed_fields.append("project")
        if source_path and str(frontmatter.get("source_path", "")).strip() != source_path:
            changed_fields.append("source_path")
        if doc_type and str(frontmatter.get("doc_type", "")).strip() != doc_type:
            changed_fields.append("doc_type")
        if tags != [str(tag) for tag in frontmatter.get("tags", []) if str(tag)]:
            changed_fields.append("tags")

        will_update = bool(changed_fields or added_links)
        items.append(
            WikiBackfillItem(
                topic=topic,
                project=project_id,
                source_path=source_path,
                doc_type=doc_type,
                changed_fields=changed_fields,
                added_links=added_links,
                updated=will_update,
            )
        )
        if not will_update:
            skipped += 1
            continue

        updated += 1
        if dry_run:
            continue

        frontmatter_extra = {}
        if project_id:
            frontmatter_extra["project"] = project_id
        if source_path:
            frontmatter_extra["source_path"] = source_path
        if doc_type:
            frontmatter_extra["doc_type"] = doc_type
        if tags:
            frontmatter_extra["tags"] = tags

        write_wiki_page(ctx.wiki_dir, topic, raw, frontmatter_extra=frontmatter_extra)
        if merged_links != existing_links:
            set_wiki_links(ctx.wiki_dir, topic, merged_links)

    return WikiBackfillResult(updated=updated, skipped=skipped, items=items)
