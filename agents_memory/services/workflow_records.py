from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from agents_memory.runtime import AppContext
from agents_memory.services.planning_core import slugify_task_name


ERROR_SOURCE_TYPES = {"", "error_record"}
WORKFLOW_SOURCE_TYPES = {
    "task_completion",
    "requirement_completion",
    "markdown",
    "text",
    "json",
    "meeting",
    "decision",
    "pr-review",
    "code-review",
}


@dataclass(frozen=True)
class StoredRecord:
    record_id: str
    path: Path


@dataclass(frozen=True)
class WorkflowMigrationItem:
    source_path: str
    target_path: str
    record_id: str
    source_type: str


@dataclass(frozen=True)
class WorkflowMigrationResult:
    migrated: list[WorkflowMigrationItem]
    skipped: list[str]
    dry_run: bool

    @property
    def migrated_count(self) -> int:
        return len(self.migrated)

    @property
    def skipped_count(self) -> int:
        return len(self.skipped)


def normalize_project_id(value: str) -> str:
    stripped = str(value or "").strip()
    if not stripped:
        return ""
    return slugify_task_name(stripped)


def source_type_from_meta(meta: dict) -> str:
    return str(meta.get("source_type", "")).strip().lower()


def is_error_record_meta(meta: dict) -> bool:
    return source_type_from_meta(meta) in ERROR_SOURCE_TYPES


def is_workflow_record_meta(meta: dict) -> bool:
    return source_type_from_meta(meta) in WORKFLOW_SOURCE_TYPES


def _parse_frontmatter_text(content: str) -> tuple[dict[str, str], str]:
    if not content.lstrip().startswith("---"):
        return {}, content

    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, content

    meta: dict[str, str] = {}
    end_index: int | None = None
    for index, line in enumerate(lines[1:], start=1):
        stripped = line.rstrip()
        if stripped == "---":
            end_index = index
            break
        if ": " in stripped:
            key, value = stripped.split(": ", 1)
            meta[key.strip()] = value.strip().strip('"')

    if end_index is None:
        return {}, content

    body = "\n".join(lines[end_index + 1 :]).lstrip("\n")
    return meta, body


def _parse_frontmatter_file(path: Path) -> dict[str, str]:
    meta, _body = _parse_frontmatter_text(path.read_text(encoding="utf-8"))
    return meta


def _read_body_file(path: Path) -> str:
    _meta, body = _parse_frontmatter_text(path.read_text(encoding="utf-8"))
    return body


def _serialize_frontmatter_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if re.fullmatch(r"[A-Za-z0-9._/@:+-]+", text):
        return text
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _render_document(meta: dict[str, object], body: str) -> str:
    lines = ["---"]
    for key, value in meta.items():
        if value in ("", None):
            continue
        lines.append(f"{key}: {_serialize_frontmatter_value(value)}")
    lines.extend(["---", ""])
    if body:
        lines.append(body.rstrip())
    return "\n".join(lines) + "\n"


def _next_error_record_id(ctx: AppContext) -> str:
    today = date.today().strftime("%Y%m%d")
    existing = list(ctx.errors_dir.glob(f"ERR-{today}-*.md"))
    return f"ERR-{today}-{len(existing) + 1:03d}"


def _resolve_workflow_record_id(ctx: AppContext, preferred_id: str, *, reserved_ids: set[str] | None = None) -> str:
    raw_id = preferred_id.strip()
    safe_id = re.sub(r"[^A-Za-z0-9._-]+", "-", raw_id).strip("-")
    base_id = safe_id or f"WFR-{date.today().strftime('%Y%m%d')}"
    candidate = base_id
    suffix = 2
    reserved = reserved_ids or set()
    while (ctx.workflow_dir / f"{candidate}.md").exists() or candidate in reserved:
        candidate = f"{base_id}-{suffix}"
        suffix += 1
    return candidate


def _prepare_document(
    content: str,
    *,
    record_id: str,
    project: str,
    source_type: str,
    default_status: str,
    date_field: str,
    external_id: str = "",
) -> str:
    existing_meta, body = _parse_frontmatter_text(content)
    meta: dict[str, object] = dict(existing_meta)
    if external_id and external_id != record_id:
        meta["external_id"] = external_id
    meta["id"] = record_id
    meta["project"] = project
    meta["source_type"] = source_type
    meta.setdefault("status", default_status)
    meta.setdefault(date_field, date.today().isoformat())
    if not body:
        body = content.strip() if not existing_meta else body
    return _render_document(meta, body)


def _store_workflow_document(
    ctx: AppContext,
    *,
    content: str,
    project: str,
    source_type: str,
    forced_record_id: str | None = None,
) -> StoredRecord:
    project_id = normalize_project_id(project)
    existing_meta, _body = _parse_frontmatter_text(content)
    upstream_id = str(existing_meta.get("id", "")).strip()
    record_id = forced_record_id or _resolve_workflow_record_id(ctx, upstream_id)
    rendered = _prepare_document(
        content,
        record_id=record_id,
        project=project_id or "unknown",
        source_type=source_type,
        default_status="completed",
        date_field="created_at",
        external_id=upstream_id,
    )
    path = ctx.workflow_dir / f"{record_id}.md"
    path.write_text(rendered, encoding="utf-8")
    return StoredRecord(record_id=record_id, path=path)


def write_error_record(
    ctx: AppContext,
    *,
    content: str,
    project: str,
    source_type: str,
) -> StoredRecord:
    project_id = normalize_project_id(project)
    existing_meta, _body = _parse_frontmatter_text(content)
    upstream_id = str(existing_meta.get("id", "")).strip()
    record_id = _next_error_record_id(ctx)
    rendered = _prepare_document(
        content,
        record_id=record_id,
        project=project_id or "unknown",
        source_type=source_type,
        default_status="new",
        date_field="date",
        external_id=upstream_id,
    )
    path = ctx.errors_dir / f"{record_id}.md"
    path.write_text(rendered, encoding="utf-8")
    return StoredRecord(record_id=record_id, path=path)


def write_workflow_record(
    ctx: AppContext,
    *,
    content: str,
    project: str,
    source_type: str,
) -> StoredRecord:
    return _store_workflow_document(ctx, content=content, project=project, source_type=source_type)


def _load_workflow_file(path: Path, *, storage_kind: str) -> dict | None:
    meta = _parse_frontmatter_file(path)
    if not meta or not is_workflow_record_meta(meta):
        return None
    normalized_project = normalize_project_id(meta.get("project", ""))
    if normalized_project:
        meta["project"] = normalized_project
    meta["_file"] = str(path)
    meta["_storage_kind"] = storage_kind
    return meta


def collect_workflow_records(ctx: AppContext, *, project: str | None = None) -> list[dict]:
    records: list[dict] = []
    normalized_project = normalize_project_id(project or "")
    seen_ids: set[str] = set()

    for path in sorted(ctx.workflow_dir.glob("*.md")):
        meta = _load_workflow_file(path, storage_kind="workflow")
        if not meta:
            continue
        if normalized_project and meta.get("project") != normalized_project:
            continue
        seen_ids.add(str(meta.get("id", "")))
        records.append(meta)

    # Keep historical compatibility: old completed task/requirement records may still
    # live under errors/ from the previous storage model.
    for path in sorted(ctx.errors_dir.glob("*.md")):
        meta = _load_workflow_file(path, storage_kind="legacy-error")
        if not meta:
            continue
        if normalized_project and meta.get("project") != normalized_project:
            continue
        record_id = str(meta.get("id", ""))
        if record_id in seen_ids:
            continue
        records.append(meta)

    return sorted(
        records,
        key=lambda item: (
            str(item.get("completed_at", "")),
            str(item.get("created_at", "")),
            str(item.get("date", "")),
            str(item.get("id", "")),
        ),
        reverse=True,
    )


def read_workflow_record(ctx: AppContext, record_id: str) -> tuple[dict, str, str] | None:
    for record in collect_workflow_records(ctx):
        current_id = str(record.get("id", "")).strip()
        if current_id != record_id:
            continue
        path = Path(str(record["_file"]))
        raw = path.read_text(encoding="utf-8")
        body = _read_body_file(path)
        return record, raw, body
    return None


def migrate_legacy_workflow_records(ctx: AppContext, *, dry_run: bool = False, limit: int | None = None) -> WorkflowMigrationResult:
    migrated: list[WorkflowMigrationItem] = []
    skipped: list[str] = []
    reserved_ids = {path.stem for path in ctx.workflow_dir.glob("*.md")}

    candidates = sorted(ctx.errors_dir.glob("*.md"))
    processed = 0
    for path in candidates:
        meta = _parse_frontmatter_file(path)
        if not meta:
            continue
        if not is_workflow_record_meta(meta):
            continue
        if limit is not None and processed >= limit:
            skipped.append(f"{path.name}: limit reached")
            continue

        record_id = str(meta.get("id", "")).strip()
        source_type = source_type_from_meta(meta)
        target_record_id = _resolve_workflow_record_id(ctx, record_id, reserved_ids=reserved_ids)
        target_path = ctx.workflow_dir / f"{target_record_id}.md"
        if target_path.exists():
            skipped.append(f"{path.name}: target already exists")
            continue

        processed += 1
        reserved_ids.add(target_record_id)
        migrated.append(
            WorkflowMigrationItem(
                source_path=str(path),
                target_path=str(target_path),
                record_id=target_record_id,
                source_type=source_type,
            )
        )
        if dry_run:
            continue

        content = path.read_text(encoding="utf-8")
        stored = _store_workflow_document(
            ctx,
            content=content,
            project=str(meta.get("project", "")),
            source_type=source_type,
            forced_record_id=target_record_id,
        )
        path.unlink()
        migrated[-1] = WorkflowMigrationItem(
            source_path=str(path),
            target_path=str(stored.path),
            record_id=stored.record_id,
            source_type=source_type,
        )

    return WorkflowMigrationResult(migrated=migrated, skipped=skipped, dry_run=dry_run)
