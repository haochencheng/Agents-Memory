from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agents_memory.runtime import AppContext
from agents_memory.services.integration import load_onboarding_state
from agents_memory.services.planning_core import (
    DEFAULT_PLAN_ROOT,
    JSON_CODE_FENCE,
    MANAGED_BUNDLE_FILENAMES,
    PLAN_PLAN_FILE,
    README_PLAN_FILE,
    SPEC_PLAN_FILE,
    TASK_GRAPH_PLAN_FILE,
    VALIDATION_PLAN_FILE,
    _planning_templates_dir,
    _render_template,
    init_plan_bundle,
    json_block,
    refresh_managed_bundle_files,
)


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
            json_block(groups, target_root=target_root),
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
            json_block(action_sequence, target_root=target_root),
            "```",
        ],
        TASK_GRAPH_PLAN_FILE: [
            "## Onboarding Task Steps",
            JSON_CODE_FENCE,
            json_block(runbook_steps, target_root=target_root),
            "```",
        ],
        VALIDATION_PLAN_FILE: [
            "## Onboarding Verification",
            f"- primary verification command: `{verify_command}`",
            f"- expected completion: {done_when}",
            "",
            "## State Snapshot",
            JSON_CODE_FENCE,
            json_block(
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
    resolved_slug = _default_onboarding_slug(target_root, recommended_key, task_slug)
    templates_dir = _planning_templates_dir(ctx)
    if not templates_dir.exists():
        raise FileNotFoundError(f"planning templates directory not found: {templates_dir}")

    plan_result = init_plan_bundle(ctx, task_name, target_root, task_slug=resolved_slug, dry_run=dry_run)
    relative_state_path = ".agents-memory/onboarding-state.json"
    created_now = set(plan_result.wrote_files)
    refreshed_files, skipped_files = refresh_managed_bundle_files(
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
        wrote_files=list(plan_result.wrote_files),
        refreshed_files=refreshed_files,
        skipped_files=skipped_files,
        dry_run=dry_run,
    )