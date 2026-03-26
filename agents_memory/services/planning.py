from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agents_memory.logging_utils import log_file_update
from agents_memory.runtime import AppContext
from agents_memory.services.integration import load_onboarding_state
from agents_memory.services.validation import RefactorHotspot, collect_refactor_watch_hotspots, serialize_refactor_hotspot


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
class OnboardingBundleResult:
    task_name: str
    task_slug: str
    target_root: Path
    plan_root: Path
    state_path: Path
    recommended_next_command: str | None
    verify_command: str | None
    wrote_files: list[str]
    refreshed_files: list[str]
    skipped_files: list[str]
    dry_run: bool


@dataclass(frozen=True)
class RefactorBundleResult:
    task_name: str
    task_slug: str
    target_root: Path
    plan_root: Path
    hotspot_index: int
    hotspot_token: str
    hotspot: RefactorHotspot
    wrote_files: list[str]
    refreshed_files: list[str]
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


def _sanitize_bundle_value(value: Any, target_root: Path) -> Any:
    root_str = str(target_root)
    if isinstance(value, str):
        return value.replace(root_str, ".")
    if isinstance(value, list):
        return [_sanitize_bundle_value(item, target_root) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize_bundle_value(item, target_root) for key, item in value.items()}
    return value


def _json_block(value: object, *, target_root: Path | None = None) -> str:
    payload = _sanitize_bundle_value(value, target_root) if target_root is not None else value
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _default_onboarding_slug(target_root: Path, recommended_key: str, task_slug: str | None) -> str:
    if task_slug:
        return task_slug
    plan_root = target_root / DEFAULT_PLAN_ROOT
    existing = sorted(path.name for path in plan_root.glob("onboarding-*") if path.is_dir()) if plan_root.exists() else []
    if len(existing) == 1:
        return existing[0]
    recommended_slug = f"onboarding-{recommended_key.replace('_', '-')}"
    if recommended_slug in existing:
        return recommended_slug
    return recommended_slug


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

    appendix_map = {
        README_PLAN_FILE: [
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
        SPEC_PLAN_FILE: [
            "## Onboarding Inputs",
            f"- state file: `{relative_state_path}`",
            "",
            JSON_CODE_FENCE,
            _json_block(groups, target_root=target_root),
            "```",
        ],
        PLAN_PLAN_FILE: [
            "## Onboarding Execution",
            f"- run `{recommended_next_command}`",
            f"- verify with `{verify_command}`",
            f"- finish when: {done_when}",
            "",
            "## Action Sequence Snapshot",
            JSON_CODE_FENCE,
            _json_block(action_sequence, target_root=target_root),
            "```",
        ],
        TASK_GRAPH_PLAN_FILE: [
            "## Onboarding Task Steps",
            JSON_CODE_FENCE,
            _json_block(runbook_steps, target_root=target_root),
            "```",
        ],
        VALIDATION_PLAN_FILE: [
            "## Onboarding Verification",
            f"- primary verification command: `{verify_command}`",
            f"- expected completion: {done_when}",
            "",
            "## State Snapshot",
            JSON_CODE_FENCE,
            _json_block(
                {
                    "project_bootstrap_ready": state.get("project_bootstrap_ready"),
                    "project_bootstrap_complete": state.get("project_bootstrap_complete"),
                    "recommended_next_command": recommended_next_command,
                    "recommended_verify_command": verify_command,
                },
                target_root=target_root,
            ),
            "```",
        ],
    }
    appendix = appendix_map.get(filename, [])
    appendix_text = "\n".join(appendix).rstrip()
    return base + ("\n\n" + appendix_text if appendix_text else "") + "\n"


def _onboarding_appendix_heading(filename: str) -> str:
    heading_map = {
        README_PLAN_FILE: "## Onboarding State",
        SPEC_PLAN_FILE: "## Onboarding Inputs",
        PLAN_PLAN_FILE: "## Onboarding Execution",
        TASK_GRAPH_PLAN_FILE: "## Onboarding Task Steps",
        VALIDATION_PLAN_FILE: "## Onboarding Verification",
    }
    return heading_map[filename]


def _refresh_managed_bundle_files(
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
    # Reuse the planning bundle scaffolder, then refresh only the managed
    # onboarding sections so human-authored context around the bundle survives.
    state = load_onboarding_state(target_root)
    if state is None:
        raise FileNotFoundError(
            f"onboarding state not found: {target_root / '.agents-memory' / 'onboarding-state.json'}"
        )

    recommended_key = str(state.get("recommended_next_key") or "onboarding")
    recommended_group = str(state.get("recommended_next_group") or "Shared Engineering Brain")
    task_name = f"{recommended_group} onboarding: {recommended_key}"
    resolved_slug = _default_onboarding_slug(target_root, recommended_key, task_slug)
    templates_dir = _planning_templates_dir(ctx)
    if not templates_dir.exists():
        raise FileNotFoundError(f"planning templates directory not found: {templates_dir}")

    plan_result = init_plan_bundle(ctx, task_name, target_root, task_slug=resolved_slug, dry_run=dry_run)
    relative_state_path = " .agents-memory/onboarding-state.json".strip()
    wrote_files: list[str] = list(plan_result.wrote_files)
    refreshed_files: list[str] = []
    skipped_files: list[str] = []

    created_now = set(plan_result.wrote_files)
    refreshed_files, skipped_files = _refresh_managed_bundle_files(
        ctx,
        target_root=target_root,
        plan_root=plan_result.plan_root,
        filenames=MANAGED_BUNDLE_FILENAMES,
        created_now=created_now,
        dry_run=dry_run,
        render_content=lambda filename: _render_onboarding_bundle_content(
            templates_dir / f"{filename.replace('.md', '')}.template.md",
            filename=filename,
            task_name=task_name,
            task_slug=resolved_slug,
            state=state,
            relative_state_path=relative_state_path,
            target_root=target_root,
        ),
        resolve_heading=_onboarding_appendix_heading,
        create_action="onboarding_bundle_file",
        refresh_action="onboarding_bundle_refresh",
        log_detail=f"task_slug={resolved_slug}",
    )

    return OnboardingBundleResult(
        task_name=task_name,
        task_slug=resolved_slug,
        target_root=target_root,
        plan_root=plan_result.plan_root,
        state_path=target_root / ".agents-memory" / "onboarding-state.json",
        recommended_next_command=str(state.get("recommended_next_command") or ""),
        verify_command=str(state.get("recommended_verify_command") or ""),
        wrote_files=wrote_files,
        refreshed_files=refreshed_files,
        skipped_files=skipped_files,
        dry_run=dry_run,
    )


def _default_refactor_slug(hotspot: RefactorHotspot, task_slug: str | None) -> str:
    base_slug = task_slug or slugify_task_name(f"{hotspot.relative_path}-{hotspot.function_name}")
    return base_slug if base_slug.startswith("refactor-") else f"refactor-{base_slug}"


def _resolve_refactor_hotspot(
    hotspots: list[RefactorHotspot],
    *,
    hotspot_index: int,
    hotspot_token: str | None,
) -> tuple[int, RefactorHotspot]:
    if hotspot_token:
        for resolved_index, candidate in enumerate(hotspots, start=1):
            if candidate.rank_token == hotspot_token:
                return resolved_index, candidate
        raise ValueError(f"hotspot token '{hotspot_token}' was not found; run `amem doctor .` or `memory_get_refactor_hotspots()` again")

    if hotspot_index < 1:
        raise ValueError("hotspot index must be >= 1")
    if hotspot_index > len(hotspots):
        raise IndexError(f"hotspot index {hotspot_index} is out of range; found {len(hotspots)} hotspot(s)")
    return hotspot_index, hotspots[hotspot_index - 1]


def _render_refactor_bundle_content(
    source: Path,
    *,
    filename: str,
    task_name: str,
    task_slug: str,
    hotspot: RefactorHotspot,
    hotspot_index: int,
    hotspot_token: str,
) -> str:
    if not source.exists():
        raise FileNotFoundError(f"planning template not found: {source}")
    base = _render_template(source, task_name=task_name, task_slug=task_slug).rstrip()

    def _json_block(value: object) -> str:
        return json.dumps(value, ensure_ascii=False, indent=2)

    hotspot_payload = serialize_refactor_hotspot(hotspot)
    init_command = f"amem refactor-bundle . --token {hotspot_token}"
    appendix_map = {
        README_PLAN_FILE: [
            "## Refactor Hotspot",
            f"- hotspot: `{hotspot.identifier}`",
            f"- hotspot token: `{hotspot_token}`",
            f"- current rank index: `{hotspot_index}`",
            f"- line: `{hotspot.line}`",
            f"- status: `{hotspot.status}`",
            f"- issues: `{', '.join(hotspot.issues)}`",
            f"- bundle entry command: `{init_command}`",
            "- verify with: `amem doctor .`",
        ],
        SPEC_PLAN_FILE: [
            "## Refactor Inputs",
            "",
            JSON_CODE_FENCE,
            _json_block(hotspot_payload),
            "```",
        ],
        PLAN_PLAN_FILE: [
            "## Refactor Execution",
            f"- Target hotspot: `{hotspot.identifier}`",
            "- Split branches/state transitions before adding new behavior.",
            "- Preserve behavior with focused tests or validation commands before and after extraction.",
            "- Re-run `amem doctor .` after the refactor and confirm the hotspot disappears or shrinks.",
        ],
        TASK_GRAPH_PLAN_FILE: [
            "## Refactor Work Items",
            JSON_CODE_FENCE,
            _json_block(
                [
                    {"step": 1, "title": "Map decision branches and data mutations", "done_when": "Current control flow is documented in spec.md."},
                    {"step": 2, "title": "Extract or simplify the hotspot", "done_when": "Complexity drivers are reduced without behavior regression."},
                    {"step": 3, "title": "Re-run validation", "done_when": "`amem doctor .` shows a smaller refactor_watch surface."},
                ]
            ),
            "```",
        ],
        VALIDATION_PLAN_FILE: [
            "## Refactor Verification",
            "- primary verification command: `amem doctor .`",
            f"- expected outcome: `{hotspot.identifier}` is no longer the first hotspot, or its issue list is smaller.",
            "",
            "## Hotspot Snapshot",
            JSON_CODE_FENCE,
            _json_block(hotspot_payload),
            "```",
        ],
    }
    appendix = appendix_map.get(filename, [])
    appendix_text = "\n".join(appendix).rstrip()
    return base + ("\n\n" + appendix_text if appendix_text else "") + "\n"


def _refactor_appendix_heading(filename: str) -> str:
    heading_map = {
        README_PLAN_FILE: "## Refactor Hotspot",
        SPEC_PLAN_FILE: "## Refactor Inputs",
        PLAN_PLAN_FILE: "## Refactor Execution",
        TASK_GRAPH_PLAN_FILE: "## Refactor Work Items",
        VALIDATION_PLAN_FILE: "## Refactor Verification",
    }
    return heading_map[filename]


def _refresh_refactor_bundle_files(
    ctx: AppContext,
    *,
    target_root: Path,
    plan_root: Path,
    templates_dir: Path,
    task_name: str,
    task_slug: str,
    hotspot: RefactorHotspot,
    hotspot_index: int,
    dry_run: bool,
    created_now: set[str],
) -> tuple[list[str], list[str]]:
    return _refresh_managed_bundle_files(
        ctx,
        target_root=target_root,
        plan_root=plan_root,
        filenames=MANAGED_BUNDLE_FILENAMES,
        created_now=created_now,
        dry_run=dry_run,
        render_content=lambda filename: _render_refactor_bundle_content(
            templates_dir / f"{filename.replace('.md', '')}.template.md",
            filename=filename,
            task_name=task_name,
            task_slug=task_slug,
            hotspot=hotspot,
            hotspot_index=hotspot_index,
            hotspot_token=hotspot.rank_token,
        ),
        resolve_heading=_refactor_appendix_heading,
        create_action="refactor_bundle_file",
        refresh_action="refactor_bundle_refresh",
        log_detail=f"task_slug={task_slug};hotspot={hotspot.identifier}",
    )


def init_refactor_bundle(
    ctx: AppContext,
    target_root: Path,
    *,
    hotspot_index: int = 1,
    hotspot_token: str | None = None,
    task_slug: str | None = None,
    dry_run: bool = False,
) -> RefactorBundleResult:
    hotspots = collect_refactor_watch_hotspots(target_root)
    if not hotspots:
        raise FileNotFoundError(f"no refactor hotspots found under: {target_root}")

    hotspot_index, hotspot = _resolve_refactor_hotspot(
        hotspots,
        hotspot_index=hotspot_index,
        hotspot_token=hotspot_token,
    )

    task_name = f"Refactor hotspot: {hotspot.identifier}"
    resolved_slug = _default_refactor_slug(hotspot, task_slug)
    templates_dir = _planning_templates_dir(ctx)
    if not templates_dir.exists():
        raise FileNotFoundError(f"planning templates directory not found: {templates_dir}")

    plan_result = init_plan_bundle(ctx, task_name, target_root, task_slug=resolved_slug, dry_run=dry_run)
    wrote_files = list(plan_result.wrote_files)
    created_now = set(plan_result.wrote_files)
    refreshed_files, skipped_files = _refresh_refactor_bundle_files(
        ctx,
        target_root=target_root,
        plan_root=plan_result.plan_root,
        templates_dir=templates_dir,
        task_name=task_name,
        task_slug=resolved_slug,
        hotspot=hotspot,
        hotspot_index=hotspot_index,
        dry_run=dry_run,
        created_now=created_now,
    )

    return RefactorBundleResult(
        task_name=task_name,
        task_slug=resolved_slug,
        target_root=target_root,
        plan_root=plan_result.plan_root,
        hotspot_index=hotspot_index,
        hotspot_token=hotspot.rank_token,
        hotspot=hotspot,
        wrote_files=wrote_files,
        refreshed_files=refreshed_files,
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
