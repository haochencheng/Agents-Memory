from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agents_memory.logging_utils import log_file_update
from agents_memory.runtime import AppContext
from agents_memory.services.integration import load_onboarding_state


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


@dataclass(frozen=True)
class OnboardingBundleResult:
    task_name: str
    task_slug: str
    target_root: Path
    plan_root: Path
    state_path: Path
    recommended_next_command: str | None
    verify_command: str | None
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


def _render_onboarding_bundle_content(
    source: Path,
    *,
    filename: str,
    task_name: str,
    task_slug: str,
    state: dict[str, object],
    relative_state_path: str,
    target_root: Path,
) -> str:
    if not source.exists():
        raise FileNotFoundError(f"planning template not found: {source}")
    base = _render_template(source, task_name=task_name, task_slug=task_slug).rstrip()
    recommended_next_command = str(state.get("recommended_next_command") or "amem doctor .")
    verify_command = str(state.get("recommended_verify_command") or "amem doctor .")
    done_when = str(state.get("recommended_done_when") or "Latest onboarding step is complete.")
    recommended_group = str(state.get("recommended_next_group") or "Unknown")
    recommended_key = str(state.get("recommended_next_key") or "unknown")
    bootstrap_ready = "yes" if bool(state.get("project_bootstrap_ready")) else "no"
    bootstrap_complete = "yes" if bool(state.get("project_bootstrap_complete")) else "no"
    action_sequence = state.get("action_sequence") or []
    runbook_steps = state.get("runbook_steps") or []
    groups = state.get("groups") or []

    def _sanitize(value: Any) -> Any:
        root_str = str(target_root)
        if isinstance(value, str):
            return value.replace(root_str, ".")
        if isinstance(value, list):
            return [_sanitize(item) for item in value]
        if isinstance(value, dict):
            return {key: _sanitize(item) for key, item in value.items()}
        return value

    def _json_block(value: object) -> str:
        return json.dumps(_sanitize(value), ensure_ascii=False, indent=2)

    appendix_map = {
        "README.md": [
            "## Onboarding State",
            f"- state file: `{relative_state_path}`",
            f"- bootstrap ready: `{bootstrap_ready}`",
            f"- bootstrap complete: `{bootstrap_complete}`",
            f"- next group: `{recommended_group}`",
            f"- next key: `{recommended_key}`",
            f"- next command: `{recommended_next_command}`",
            f"- verify with: `{verify_command}`",
            f"- done when: {done_when}",
        ],
        "spec.md": [
            "## Onboarding Inputs",
            f"- state file: `{relative_state_path}`",
            "",
            "```json",
            _json_block(groups),
            "```",
        ],
        "plan.md": [
            "## Onboarding Execution",
            f"- run `{recommended_next_command}`",
            f"- verify with `{verify_command}`",
            f"- finish when: {done_when}",
            "",
            "## Action Sequence Snapshot",
            "```json",
            _json_block(action_sequence),
            "```",
        ],
        "task-graph.md": [
            "## Onboarding Task Steps",
            "```json",
            _json_block(runbook_steps),
            "```",
        ],
        "validation.md": [
            "## Onboarding Verification",
            f"- primary verification command: `{verify_command}`",
            f"- expected completion: {done_when}",
            "",
            "## State Snapshot",
            "```json",
            _json_block(
                {
                    "project_bootstrap_ready": state.get("project_bootstrap_ready"),
                    "project_bootstrap_complete": state.get("project_bootstrap_complete"),
                    "recommended_next_command": recommended_next_command,
                    "recommended_verify_command": verify_command,
                }
            ),
            "```",
        ],
    }
    appendix = appendix_map.get(filename, [])
    return base + ("\n\n" + "\n".join(appendix) if appendix else "") + "\n"


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


def init_onboarding_bundle(
    ctx: AppContext,
    target_root: Path,
    *,
    task_slug: str | None = None,
    dry_run: bool = False,
) -> OnboardingBundleResult:
    state = load_onboarding_state(target_root)
    if state is None:
        raise FileNotFoundError(
            f"onboarding state not found: {target_root / '.agents-memory' / 'onboarding-state.json'}"
        )

    recommended_key = str(state.get("recommended_next_key") or "onboarding")
    recommended_group = str(state.get("recommended_next_group") or "Shared Engineering Brain")
    task_name = f"{recommended_group} onboarding: {recommended_key}"
    resolved_slug = task_slug or f"onboarding-{recommended_key.replace('_', '-')}"
    templates_dir = _planning_templates_dir(ctx)
    if not templates_dir.exists():
        raise FileNotFoundError(f"planning templates directory not found: {templates_dir}")

    plan_result = init_plan_bundle(ctx, task_name, target_root, task_slug=resolved_slug, dry_run=dry_run)
    relative_state_path = " .agents-memory/onboarding-state.json".strip()
    wrote_files = list(plan_result.wrote_files)
    skipped_files = list(plan_result.skipped_files)

    for filename in ["README.md", "spec.md", "plan.md", "task-graph.md", "validation.md"]:
        destination = plan_result.plan_root / filename
        relative = destination.relative_to(target_root).as_posix()
        template_path = templates_dir / f"{filename.replace('.md', '')}.template.md"
        rendered = _render_onboarding_bundle_content(
            template_path,
            filename=filename,
            task_name=task_name,
            task_slug=resolved_slug,
            state=state,
            relative_state_path=relative_state_path,
            target_root=target_root,
        )
        if destination.exists() and relative in skipped_files:
            continue
        if dry_run:
            if relative not in wrote_files:
                wrote_files.append(relative)
            continue
        destination.write_text(rendered, encoding="utf-8")
        log_file_update(ctx.logger, action="onboarding_bundle_file", path=destination, detail=f"task_slug={resolved_slug}")

    return OnboardingBundleResult(
        task_name=task_name,
        task_slug=resolved_slug,
        target_root=target_root,
        plan_root=plan_result.plan_root,
        state_path=target_root / ".agents-memory" / "onboarding-state.json",
        recommended_next_command=str(state.get("recommended_next_command") or ""),
        verify_command=str(state.get("recommended_verify_command") or ""),
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

    if result.wrote_files:
        print("\nWrote Files:")
        for item in result.wrote_files:
            print(f"- {item}")
    if result.skipped_files:
        print("\nSkipped Files:")
        for item in result.skipped_files:
            print(f"- {item}")
    if result.dry_run:
        return
    print("\nNext:")
    print(f"- Run {result.recommended_next_command or 'amem doctor .'}")
    print(f"- Verify with {result.verify_command or 'amem doctor .'}")
    print(f"- Review {result.plan_root / 'plan.md'} before executing onboarding work")


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
        len(result.wrote_files),
        len(result.skipped_files),
    )
    return 0
