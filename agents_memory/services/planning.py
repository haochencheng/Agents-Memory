from __future__ import annotations

from pathlib import Path

from agents_memory.runtime import AppContext
from agents_memory.services.planning_core import (
    NEXT_SECTION_HEADING,
    PlanInitResult,
    PlanRepairResult,
    init_plan_bundle,
    repair_plan_bundles,
    slugify_task_name,
)
from agents_memory.services.planning_onboarding import OnboardingBundleResult, init_onboarding_bundle
from agents_memory.services.planning_refactor import RefactorBundleResult, init_refactor_bundle


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

    print(NEXT_SECTION_HEADING)
    print(f"- Review {result.plan_root / 'spec.md'} and fill in acceptance criteria")
    print(f"- Review {result.plan_root / 'task-graph.md'} before changing code")
    print("- Run docs-check after the implementation is complete")


def _print_bundle_file_groups(*, wrote_files: list[str], refreshed_files: list[str] | None = None, skipped_files: list[str]) -> None:
    sections = [
        ("Wrote Files", wrote_files),
        ("Refreshed Files", refreshed_files or []),
        ("Skipped Files", skipped_files),
    ]
    for title, items in sections:
        if not items:
            continue
        print(f"\n{title}:")
        for item in items:
            print(f"- {item}")


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


def _print_onboarding_bundle_summary(result: OnboardingBundleResult) -> None:
    heading = "Onboarding Bundle Preview" if result.dry_run else "Onboarding Bundle"
    print(f"\n=== {heading} ===")
    print(f"Task:      {result.task_name}")
    print(f"Slug:      {result.task_slug}")
    print(f"Target:    {result.target_root}")
    print(f"PlanDir:   {result.plan_root}")
    print(f"State:     {result.state_path}")
    print(f"DryRun:    {'yes' if result.dry_run else 'no'}")
    print(f"NextCmd:   {result.recommended_next_command or 'n/a'}")
    print(f"VerifyCmd: {result.verify_command or 'n/a'}")
    _print_bundle_file_groups(
        wrote_files=result.wrote_files,
        refreshed_files=result.refreshed_files,
        skipped_files=result.skipped_files,
    )
    if result.dry_run:
        return
    print(NEXT_SECTION_HEADING)
    print(f"- Run {result.recommended_next_command or 'amem doctor .'}")
    print(f"- Verify with {result.verify_command or 'amem doctor .'}")
    print(f"- Review {result.plan_root / 'plan.md'} before executing onboarding work")


def _print_refactor_bundle_summary(result: RefactorBundleResult) -> None:
    heading = "Refactor Bundle Preview" if result.dry_run else "Refactor Bundle"
    print(f"\n=== {heading} ===")
    print(f"Task:      {result.task_name}")
    print(f"Slug:      {result.task_slug}")
    print(f"Target:    {result.target_root}")
    print(f"PlanDir:   {result.plan_root}")
    print(f"Hotspot:   {result.hotspot.identifier}")
    print(f"IssueSet:  {', '.join(result.hotspot.issues)}")
    print(f"DryRun:    {'yes' if result.dry_run else 'no'}")
    _print_bundle_file_groups(
        wrote_files=result.wrote_files,
        refreshed_files=result.refreshed_files,
        skipped_files=result.skipped_files,
    )
    if result.dry_run:
        return
    print(NEXT_SECTION_HEADING)
    print(f"- Review {result.plan_root / 'spec.md'} and lock acceptance criteria for {result.hotspot.identifier}")
    print(f"- Refactor {result.hotspot.identifier} before adding more behavior")
    print("- Re-run amem doctor . and confirm refactor_watch shrinks")


def cmd_onboarding_bundle(
    ctx: AppContext,
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
        "onboarding_bundle_start | task_slug=%s | target_root=%s | dry_run=%s",
        task_slug,
        target_root,
        dry_run,
    )
    result = init_onboarding_bundle(ctx, target_root, task_slug=task_slug, dry_run=dry_run)
    _print_onboarding_bundle_summary(result)
    ctx.logger.info(
        "onboarding_bundle_complete | task_slug=%s | target_root=%s | dry_run=%s | files=%s | skipped=%s",
        result.task_slug,
        result.target_root,
        result.dry_run,
        len(result.wrote_files) + len(result.refreshed_files),
        len(result.skipped_files),
    )
    return 0


def cmd_refactor_bundle(
    ctx: AppContext,
    project_id_or_path: str = ".",
    *,
    hotspot_index: int = 1,
    hotspot_token: str | None = None,
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
        "refactor_bundle_start | task_slug=%s | hotspot_index=%s | hotspot_token=%s | target_root=%s | dry_run=%s",
        task_slug,
        hotspot_index,
        hotspot_token,
        target_root,
        dry_run,
    )
    try:
        result = init_refactor_bundle(
            ctx,
            target_root,
            hotspot_index=hotspot_index,
            hotspot_token=hotspot_token,
            task_slug=task_slug,
            dry_run=dry_run,
        )
    except (FileNotFoundError, IndexError, ValueError) as exc:
        print(str(exc))
        return 1
    _print_refactor_bundle_summary(result)
    ctx.logger.info(
        "refactor_bundle_complete | task_slug=%s | hotspot_index=%s | hotspot_token=%s | target_root=%s | dry_run=%s | files=%s | skipped=%s",
        result.task_slug,
        hotspot_index,
        result.hotspot_token,
        result.target_root,
        result.dry_run,
        len(result.wrote_files) + len(result.refreshed_files),
        len(result.skipped_files),
    )
    return 0
