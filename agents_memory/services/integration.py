from __future__ import annotations

from pathlib import Path

from agents_memory.constants import DEFAULT_BRIDGE_INSTRUCTION_REL, MCP_CONFIG_NAME, PYTHON_BIN, REGISTER_HINT, VSCODE_DIRNAME
from agents_memory.integrations.agents.registry import DEFAULT_AGENT, get_agent_adapter
from agents_memory.runtime import AppContext
from agents_memory.services.integration_doctor import (
    _doctor_action_sequence,
    _doctor_bootstrap_checklist,
    _doctor_bridge_check,
    _doctor_group_checks,
    _doctor_group_remediations,
    _doctor_group_status,
    _doctor_group_summary,
    _doctor_overall,
    _doctor_planning_checks,
    _doctor_refactor_watch_checks,
    _doctor_report,
    _doctor_runbook_steps,
    _recommended_step_metadata,
    _report_grouped_checks,
    _report_project_root,
    _report_steps,
    _result_mapping,
    _result_string_list,
    _runbook_step_from_state,
    _state_pending_steps,
    _state_recommended_steps,
    _write_doctor_artifacts,
    _write_onboarding_state_file,
    cmd_doctor,
    load_onboarding_state,
    onboarding_next_action,
    onboarding_state_path,
)
from agents_memory.services.integration_enable import cmd_enable as run_enable_command
from agents_memory.services.integration_onboarding import cmd_onboarding_execute, execute_onboarding_next_action
from agents_memory.services.integration_register import cmd_register
from agents_memory.services.integration_setup import (
    cmd_agent_list,
    cmd_agent_setup,
    cmd_bridge_install,
    cmd_copilot_setup,
    cmd_mcp_setup,
    cmd_sync,
    mcp_package_ready,
    python_ready,
    write_vscode_mcp_json,
)
from agents_memory.services.projects import (
    parse_projects,
    resolve_bridge_rel,
    resolve_project_target,
)
from agents_memory.services.profiles import detect_applied_profile, load_profile, profile_agents_router_status
from agents_memory.services.validation import collect_refactor_watch_hotspots


def _build_refactor_followup_step(
    bundle_rel: str,
    hotspot_identifier: str,
    hotspot_token: str,
    task_name: str,
    task_slug: str,
    hotspot_index: int,
    hotspot: dict,
) -> dict[str, object]:
    # Build the recommended-step dict that describes the generated refactor bundle.
    command = f"python3 scripts/memory.py refactor-bundle . --token {hotspot_token}"
    return {
        "group": "Refactor",
        "priority": "recommended",
        "key": "refactor_bundle",
        "status": "WARN",
        "detail": f"refactor bundle ready for {hotspot_identifier}",
        "action": f"Review and execute the generated refactor bundle at {bundle_rel} before adding more behavior.",
        "command": command,
        "verify_with": "amem doctor .",
        "done_when": f"`amem doctor .` no longer reports `{hotspot_identifier}` as the top refactor hotspot.",
        "safe_to_auto_execute": True,
        "approval_required": False,
        "approval_reason": "refreshes generated planning docs only",
        "next_command": "amem doctor .",
        "bundle_path": bundle_rel,
        "task_name": task_name,
        "task_slug": task_slug,
        "hotspot_index": hotspot_index,
        "hotspot_token": hotspot_token,
        "hotspot": hotspot,
    }


def _merge_refactor_followup_state(
    state: dict[str, object] | None,
    *,
    project_root: Path,
    plan_root: Path,
    hotspot_index: int,
    hotspot_token: str,
    hotspot: dict[str, object],
    task_name: str,
    task_slug: str,
) -> dict[str, object]:
    # Merge a new refactor follow-up recommended step into the current onboarding state.
    payload = dict(state or {})
    payload.setdefault("project_root", str(project_root))
    payload.setdefault("project_bootstrap_ready", True)
    payload.setdefault("project_bootstrap_complete", True)
    existing_recommended = _state_recommended_steps(payload)
    bundle_rel = plan_root.relative_to(project_root).as_posix()
    hotspot_identifier = str(hotspot.get("identifier") or f"index-{hotspot_index}")
    step = _build_refactor_followup_step(bundle_rel, hotspot_identifier, hotspot_token, task_name, task_slug, hotspot_index, hotspot)
    filtered = [item for item in existing_recommended if item.get("key") != "refactor_bundle"]
    payload["recommended_steps"] = [step, *filtered]
    payload["recommended_refactor_bundle"] = {
        "bundle_path": bundle_rel,
        "task_name": task_name,
        "task_slug": task_slug,
        "hotspot_index": hotspot_index,
        "hotspot_token": hotspot_token,
        "hotspot": hotspot,
    }
    if not _state_pending_steps(payload):
        payload.update(_recommended_step_metadata(step))
    return payload


def cmd_enable(
    ctx: AppContext,
    project_id_or_path: str = ".",
    *,
    full: bool = False,
    dry_run: bool = False,
    json_output: bool = False,
    ingest_wiki: bool = False,
    wiki_limit: int | None = None,
) -> int:
    return run_enable_command(
        ctx,
        project_id_or_path,
        full=full,
        dry_run=dry_run,
        json_output=json_output,
        ingest_wiki=ingest_wiki,
        wiki_limit=wiki_limit,
        doctor_report_fn=_doctor_report,
        doctor_command_fn=lambda hook_ctx, target: cmd_doctor(hook_ctx, target, write_state=True, write_checklist=True),
        load_state_fn=load_onboarding_state,
        merge_refactor_state_fn=_merge_refactor_followup_state,
        write_state_fn=_write_onboarding_state_file,
    )
