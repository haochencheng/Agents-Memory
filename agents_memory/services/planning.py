from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from agents_memory.logging_utils import log_file_update
from agents_memory.runtime import AppContext


PLANNING_TEMPLATE_DIR = Path("templates") / "planning"
DEFAULT_PLAN_ROOT = Path("docs") / "plans"


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


def slugify_task_name(task_name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", task_name.strip().lower()).strip("-")
    return cleaned or "untitled-task"


def _planning_templates_dir(ctx: AppContext) -> Path:
    return ctx.base_dir / PLANNING_TEMPLATE_DIR


def _render_template(source: Path, *, task_name: str, task_slug: str) -> str:
    content = source.read_text(encoding="utf-8")
    return content.replace("{{TASK_NAME}}", task_name).replace("{{TASK_SLUG}}", task_slug)


def _target_plan_root(target_root: Path, task_slug: str) -> Path:
    return target_root / DEFAULT_PLAN_ROOT / task_slug


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
    created_dirs: list[str] = []
    wrote_files: list[str] = []
    skipped_files: list[str] = []

    for directory in [target_root / "docs", target_root / "docs" / "plans", plan_root]:
        relative = directory.relative_to(target_root).as_posix()
        if directory.exists():
            continue
        created_dirs.append(relative)
        if dry_run:
            continue
        directory.mkdir(parents=True, exist_ok=True)
        log_file_update(ctx.logger, action="plan_init_dir", path=directory, detail=f"task_slug={resolved_slug}")

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
            _render_template(source, task_name=task_name, task_slug=resolved_slug),
            encoding="utf-8",
        )
        log_file_update(ctx.logger, action="plan_init_file", path=destination, detail=f"task_slug={resolved_slug}")

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


def _print_plan_init_summary(result: PlanInitResult) -> None:
    heading = "Plan Init Preview" if result.dry_run else "Plan Init"
    print(f"\n=== {heading} ===")
    print(f"Task:    {result.task_name}")
    print(f"Slug:    {result.task_slug}")
    print(f"Target:  {result.target_root}")
    print(f"PlanDir: {result.plan_root}")
    print(f"DryRun:  {'yes' if result.dry_run else 'no'}\n")
    print(f"- created dirs: {len(result.created_dirs)}")
    print(f"- wrote files: {len(result.wrote_files)}")
    print(f"- skipped files: {len(result.skipped_files)}")

    for title, items in (
        ("Created Dirs", result.created_dirs),
        ("Wrote Files", result.wrote_files),
        ("Skipped Files", result.skipped_files),
    ):
        if not items:
            continue
        print(f"\n{title}:")
        for item in items:
            print(f"- {item}")

    if result.dry_run:
        return

    print("\nNext:")
    print(f"- Review {result.plan_root / 'spec.md'} and fill in acceptance criteria")
    print(f"- Review {result.plan_root / 'task-graph.md'} before changing code")
    print("- Run docs-check after the implementation is complete")


def cmd_plan_init(
    ctx: AppContext,
    task_name: str,
    project_id_or_path: str = ".",
    *,
    task_slug: str | None = None,
    dry_run: bool = False,
) -> int:
    target_root = Path(project_id_or_path).expanduser().resolve()
    if not target_root.exists():
        print(f"路径不存在: {target_root}")
        return 1
    if not target_root.is_dir():
        print(f"目标不是目录: {target_root}")
        return 1

    ctx.logger.info(
        "plan_init_start | task_name=%s | task_slug=%s | target_root=%s | dry_run=%s",
        task_name,
        task_slug,
        target_root,
        dry_run,
    )
    result = init_plan_bundle(ctx, task_name, target_root, task_slug=task_slug, dry_run=dry_run)
    _print_plan_init_summary(result)
    ctx.logger.info(
        "plan_init_complete | task_name=%s | task_slug=%s | target_root=%s | dry_run=%s | dirs=%s | files=%s | skipped=%s",
        result.task_name,
        result.task_slug,
        result.target_root,
        result.dry_run,
        len(result.created_dirs),
        len(result.wrote_files),
        len(result.skipped_files),
    )
    return 0
