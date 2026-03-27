from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from agents_memory.logging_utils import log_file_update
from agents_memory.runtime import AppContext


PLANNING_TEMPLATE_DIR = Path("templates") / "planning"
DEFAULT_PLAN_ROOT = Path("docs") / "plans"
README_PLAN_FILE = "README.md"
SPEC_PLAN_FILE = "spec.md"
PLAN_PLAN_FILE = "plan.md"
TASK_GRAPH_PLAN_FILE = "task-graph.md"
VALIDATION_PLAN_FILE = "validation.md"
MANAGED_BUNDLE_FILENAMES = (
    README_PLAN_FILE,
    SPEC_PLAN_FILE,
    PLAN_PLAN_FILE,
    TASK_GRAPH_PLAN_FILE,
    VALIDATION_PLAN_FILE,
)
JSON_CODE_FENCE = "```json"
NEXT_SECTION_HEADING = "\nNext:"


@dataclass(frozen=True)
class PlanInitResult:
    task_name: str
    task_slug: str
    target_root: Path
    plan_root: Path
    created_dirs: list[str]
    wrote_files: list[str]
    skipped_files: list[str]
    dry_run: bool


@dataclass(frozen=True)
class PlanRepairResult:
    target_root: Path
    repaired_files: list[str]
    skipped_bundles: list[str]
    dry_run: bool


def slugify_task_name(task_name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", task_name.strip().lower()).strip("-")
    return cleaned or "untitled-task"


def _planning_templates_dir(ctx: AppContext) -> Path:
    return ctx.base_dir / PLANNING_TEMPLATE_DIR


def _render_template(source: Path, *, task_name: str, task_slug: str) -> str:
    content = source.read_text(encoding="utf-8")
    today = date.today().isoformat()
    return (
        content.replace("{{TASK_NAME}}", task_name)
        .replace("{{TASK_SLUG}}", task_slug)
        .replace("{{DOC_CREATED_AT}}", today)
        .replace("{{DOC_UPDATED_AT}}", today)
    )


def _merge_managed_section(existing_content: str, rendered_content: str, heading: str) -> str:
    existing = existing_content.rstrip()
    rendered = rendered_content.rstrip()
    marker = f"\n{heading}\n"
    rendered_heading_marker = f"\n{heading}\n"
    if rendered_heading_marker in rendered:
        rendered_suffix = rendered.split(rendered_heading_marker, 1)[1].lstrip()
    elif rendered.startswith(f"{heading}\n"):
        rendered_suffix = rendered.split(f"{heading}\n", 1)[1].lstrip()
    else:
        rendered_suffix = rendered
    if marker in existing:
        prefix = existing.split(marker, 1)[0].rstrip()
        return prefix + "\n\n" + heading + "\n" + rendered_suffix + "\n"
    if existing.startswith(f"{heading}\n"):
        return heading + "\n" + rendered_suffix + "\n"
    if existing.endswith(heading):
        prefix = existing[: -len(heading)].rstrip()
        return prefix + "\n\n" + heading + "\n" + rendered_suffix + "\n"
    return existing + "\n\n" + heading + "\n" + rendered_suffix + "\n"


def _target_plan_root(target_root: Path, task_slug: str) -> Path:
    return target_root / DEFAULT_PLAN_ROOT / task_slug


def _resolve_plan_bundle_targets(target_root: Path) -> tuple[Path, list[Path]]:
    plans_root = target_root / DEFAULT_PLAN_ROOT
    bundles = sorted(path for path in plans_root.iterdir() if path.is_dir()) if plans_root.exists() else []
    return target_root, bundles


def _sanitize_bundle_value(value: Any, target_root: Path) -> Any:
    root_str = str(target_root)
    if isinstance(value, str):
        return value.replace(root_str, ".")
    if isinstance(value, list):
        return [_sanitize_bundle_value(item, target_root) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize_bundle_value(item, target_root) for key, item in value.items()}
    return value


def json_block(value: object, *, target_root: Path | None = None) -> str:
    payload = _sanitize_bundle_value(value, target_root) if target_root is not None else value
    return json.dumps(payload, ensure_ascii=False, indent=2)


def refresh_managed_bundle_files(
    ctx: AppContext,
    *,
    target_root: Path,
    plan_root: Path,
    filenames: tuple[str, ...],
    created_now: set[str],
    dry_run: bool,
    render_content: Callable[[str], str],
    resolve_heading: Callable[[str], str],
    create_action: str,
    refresh_action: str,
    log_detail: str,
) -> tuple[list[str], list[str]]:
    refreshed_files: list[str] = []
    skipped_files: list[str] = []
    if dry_run:
        return refreshed_files, skipped_files

    for filename in filenames:
        destination = plan_root / filename
        if not destination.exists():
            continue
        relative = destination.relative_to(target_root).as_posix()
        existing = destination.read_text(encoding="utf-8")
        merged = _merge_managed_section(existing, render_content(filename), resolve_heading(filename))
        if merged == existing:
            if relative not in created_now:
                skipped_files.append(relative)
            continue
        destination.write_text(merged, encoding="utf-8")
        if relative in created_now:
            log_file_update(ctx.logger, action=create_action, path=destination, detail=log_detail)
            continue
        refreshed_files.append(relative)
        log_file_update(ctx.logger, action=refresh_action, path=destination, detail=log_detail)

    return refreshed_files, skipped_files


def _ensure_plan_directories(
    ctx: AppContext,
    *,
    target_root: Path,
    plan_root: Path,
    task_slug: str,
    dry_run: bool,
) -> list[str]:
    created_dirs: list[str] = []
    for directory in (target_root / "docs", target_root / "docs" / "plans", plan_root):
        relative = directory.relative_to(target_root).as_posix()
        if directory.exists():
            continue
        created_dirs.append(relative)
        if dry_run:
            continue
        directory.mkdir(parents=True, exist_ok=True)
        log_file_update(ctx.logger, action="plan_init_dir", path=directory, detail=f"task_slug={task_slug}")
    return created_dirs


def _write_plan_template_files(
    ctx: AppContext,
    *,
    templates_dir: Path,
    plan_root: Path,
    target_root: Path,
    task_name: str,
    task_slug: str,
    dry_run: bool,
) -> tuple[list[str], list[str]]:
    wrote_files: list[str] = []
    skipped_files: list[str] = []
    for source in sorted(templates_dir.glob("*.md")):
        destination_name = source.name.replace(".template", "")
        destination = plan_root / destination_name
        relative = destination.relative_to(target_root).as_posix()
        if destination.exists():
            skipped_files.append(relative)
            continue
        wrote_files.append(relative)
        if dry_run:
            continue
        destination.write_text(
            _render_template(source, task_name=task_name, task_slug=task_slug),
            encoding="utf-8",
        )
        log_file_update(ctx.logger, action="plan_init_file", path=destination, detail=f"task_slug={task_slug}")
    return wrote_files, skipped_files


def _task_name_from_plan_slug(task_slug: str) -> str:
    words = [part for part in task_slug.replace("_", "-").split("-") if part]
    if not words:
        return "Untitled Task"
    return " ".join(word.capitalize() for word in words)


def init_plan_bundle(
    ctx: AppContext,
    task_name: str,
    target_root: Path,
    *,
    task_slug: str | None = None,
    dry_run: bool = False,
) -> PlanInitResult:
    resolved_slug = task_slug or slugify_task_name(task_name)
    templates_dir = _planning_templates_dir(ctx)
    if not templates_dir.exists():
        raise FileNotFoundError(f"planning templates directory not found: {templates_dir}")

    plan_root = _target_plan_root(target_root, resolved_slug)
    created_dirs = _ensure_plan_directories(
        ctx,
        target_root=target_root,
        plan_root=plan_root,
        task_slug=resolved_slug,
        dry_run=dry_run,
    )
    wrote_files, skipped_files = _write_plan_template_files(
        ctx,
        templates_dir=templates_dir,
        plan_root=plan_root,
        target_root=target_root,
        task_name=task_name,
        task_slug=resolved_slug,
        dry_run=dry_run,
    )

    return PlanInitResult(
        task_name=task_name,
        task_slug=resolved_slug,
        target_root=target_root,
        plan_root=plan_root,
        created_dirs=created_dirs,
        wrote_files=wrote_files,
        skipped_files=skipped_files,
        dry_run=dry_run,
    )


def repair_plan_bundles(
    ctx: AppContext,
    target_root: Path,
    *,
    dry_run: bool = False,
) -> PlanRepairResult:
    templates_dir = _planning_templates_dir(ctx)
    if not templates_dir.exists():
        raise FileNotFoundError(f"planning templates directory not found: {templates_dir}")

    root, bundles = _resolve_plan_bundle_targets(target_root)
    repaired_files: list[str] = []
    skipped_bundles: list[str] = []

    for bundle in bundles:
        task_slug = bundle.name
        task_name = _task_name_from_plan_slug(task_slug)
        wrote_files, _skipped_files = _write_plan_template_files(
            ctx,
            templates_dir=templates_dir,
            plan_root=bundle,
            target_root=root,
            task_name=task_name,
            task_slug=task_slug,
            dry_run=dry_run,
        )
        if wrote_files:
            repaired_files.extend(wrote_files)
            continue
        skipped_bundles.append(bundle.relative_to(root).as_posix())

    return PlanRepairResult(
        target_root=root,
        repaired_files=repaired_files,
        skipped_bundles=skipped_bundles,
        dry_run=dry_run,
    )