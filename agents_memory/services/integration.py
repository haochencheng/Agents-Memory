from __future__ import annotations

import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import json

from agents_memory.constants import DEFAULT_BRIDGE_INSTRUCTION_REL, MCP_CONFIG_NAME, PYTHON_BIN, REGISTER_HINT, VSCODE_DIRNAME
from agents_memory.integrations.agents.registry import DEFAULT_AGENT, get_agent_adapter
from agents_memory.logging_utils import log_file_update
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
    payload = dict(state or {})
    payload.setdefault("project_root", str(project_root))
    payload.setdefault("project_bootstrap_ready", True)
    payload.setdefault("project_bootstrap_complete", True)
    existing_recommended = _state_recommended_steps(payload)
    bundle_rel = plan_root.relative_to(project_root).as_posix()
    hotspot_identifier = str(hotspot.get("identifier") or f"index-{hotspot_index}")
    command = f"python3 scripts/memory.py refactor-bundle . --token {hotspot_token}"
    step = {
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


def _runbook_step_from_state(state: dict[str, object]) -> dict[str, object] | None:
    pending_steps = _state_pending_steps(state)
    if pending_steps:
        return pending_steps[0]
    recommended_steps = _state_recommended_steps(state)
    if recommended_steps:
        return recommended_steps[0]
    return None


def _print_onboarding_execute_header(project_root: Path, *, status: str) -> None:
    print("\n=== Onboarding Execute ===")
    print(f"Project Root: {project_root}")
    print(f"Status:       {status}")


def _print_onboarding_execute_pending(result: dict[str, object], *, project_root: Path, status: str) -> None:
    _print_onboarding_execute_header(project_root, status=status)
    print(f"Message:      {result.get('message')}")
    approval_reason = result.get("approval_reason")
    if approval_reason:
        print(f"Approval:     {approval_reason}")
    recommended_command = result.get("recommended_command")
    if recommended_command:
        print(f"Next:         {recommended_command}")


def _print_onboarding_execution_block(execution: dict[str, object]) -> None:
    print(f"Command:      {execution.get('command')}")
    print(f"Resolved:     {execution.get('resolved_command')}")
    print(f"Return Code:  {execution.get('returncode')}")
    if execution.get("stdout"):
        print("\nExecution stdout:")
        print(execution["stdout"])
    if execution.get("stderr"):
        print("\nExecution stderr:")
        print(execution["stderr"])


def _print_onboarding_verify_block(verify_result: dict[str, object]) -> None:
    if not verify_result:
        return

    print("\nVerification:")
    print(f"- Command: {verify_result.get('command')}")
    print(f"- Resolved: {verify_result.get('resolved_command')}")
    print(f"- Return Code: {verify_result.get('returncode')}")
    if verify_result.get("stdout"):
        print("\nVerification stdout:")
        print(verify_result["stdout"])
    if verify_result.get("stderr"):
        print("\nVerification stderr:")
        print(verify_result["stderr"])


def _print_onboarding_state_block(result: dict[str, object]) -> None:
    print("\nState:")
    print(f"- Updated: {result.get('state_updated')}")
    print(f"- Artifacts refreshed: {result.get('artifacts_refreshed')}")
    print(f"- Approval used: {result.get('approval_used')}")
    for path in _result_string_list(result.get("written_artifacts")):
        print(f"- {path}")


def _print_onboarding_next_action(result: dict[str, object]) -> None:
    next_action = _result_mapping(result.get("next_action"))
    if not next_action:
        return

    print("\nNext Action:")
    print(f"- Status: {next_action.get('status')}")
    if next_action.get("command"):
        print(f"- Command: {next_action.get('command')}")
    elif next_action.get("recommended_command"):
        print(f"- Command: {next_action.get('recommended_command')}")


def _quoted_command(parts: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def _resolve_onboarding_command(ctx: AppContext, command: str) -> tuple[list[str], str]:
    parts = shlex.split(command)
    if not parts:
        raise ValueError("Onboarding command is empty.")

    script_path = ctx.base_dir / "scripts" / "memory.py"
    python_bin = sys.executable or shutil.which(PYTHON_BIN) or PYTHON_BIN

    if parts[0] == "amem":
        resolved = [python_bin, str(script_path), *parts[1:]]
        return resolved, _quoted_command(resolved)

    if parts[0].startswith("python") and len(parts) >= 2 and Path(parts[1]).as_posix() == "scripts/memory.py":
        resolved = [python_bin, str(script_path), *parts[2:]]
        return resolved, _quoted_command(resolved)

    return parts, _quoted_command(parts)


def _command_result_payload(command: str, resolved_command: str, completed: subprocess.CompletedProcess[str]) -> dict[str, object]:
    return {
        "command": command,
        "resolved_command": resolved_command,
        "returncode": completed.returncode,
        "stdout": (completed.stdout or "").strip(),
        "stderr": (completed.stderr or "").strip(),
        "success": completed.returncode == 0,
    }


def _run_onboarding_command(ctx: AppContext, project_root: Path, command: str) -> dict[str, object]:
    resolved_parts, resolved_display = _resolve_onboarding_command(ctx, command)
    completed = subprocess.run(
        resolved_parts,
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    payload = _command_result_payload(command, resolved_display, completed)
    ctx.logger.info(
        "onboarding_command_complete | root=%s | command=%s | resolved=%s | returncode=%s",
        project_root,
        command,
        resolved_display,
        completed.returncode,
    )
    return payload


def _merge_onboarding_execution_state(state: dict[str, object] | None, event: dict[str, object]) -> dict[str, object]:
    payload = dict(state or {})
    history = payload.get("execution_history")
    if not isinstance(history, list):
        history = []
    history.append(event)
    payload["execution_history"] = history[-20:]
    payload["last_executed_action"] = {
        "group": event.get("group"),
        "key": event.get("key"),
        "priority": event.get("priority"),
        "command": event.get("command"),
        "resolved_command": event.get("resolved_command"),
        "safe_to_auto_execute": event.get("safe_to_auto_execute"),
        "approval_required": event.get("approval_required"),
        "approval_reason": event.get("approval_reason"),
        "approve_unsafe": event.get("approve_unsafe"),
        "executed_at": event.get("executed_at"),
        "returncode": event.get("execution_returncode"),
        "success": event.get("execution_success"),
        "status": event.get("status"),
    }
    payload["last_execution_status"] = event.get("status")
    payload["last_execution_at"] = event.get("executed_at")
    if event.get("verification_run"):
        payload["last_verified_action"] = {
            "group": event.get("group"),
            "key": event.get("key"),
            "verify_with": event.get("verify_with"),
            "resolved_verify_with": event.get("resolved_verify_with"),
            "safe_to_auto_execute": event.get("safe_to_auto_execute"),
            "approval_required": event.get("approval_required"),
            "approval_reason": event.get("approval_reason"),
            "approve_unsafe": event.get("approve_unsafe"),
            "verified_at": event.get("verified_at"),
            "returncode": event.get("verification_returncode"),
            "success": event.get("verification_success"),
            "status": event.get("status"),
        }
    return payload


def _write_onboarding_state_file(ctx: AppContext, project_root: Path, state: dict[str, object]) -> Path:
    state_path = onboarding_state_path(project_root)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log_file_update(ctx.logger, action="write_onboarding_state", path=state_path, detail=f"project_root={project_root}")
    return state_path


def execute_onboarding_next_action(
    ctx: AppContext,
    project_root: Path,
    *,
    verify: bool = True,
    approve_unsafe: bool = False,
    refresh_artifacts: bool = True,
) -> dict[str, object]:
    # This is the execution core for onboarding: it enforces the approval gate,
    # runs the action, optionally verifies it, then merges the outcome back into
    # the exported onboarding state so later agents can continue from that state.
    state = load_onboarding_state(project_root)
    action = onboarding_next_action(project_root)
    if action["status"] != "pending":
        return action

    step = _runbook_step_from_state(state or {})
    if step is None:
        return {
            "status": "invalid",
            "project_root": str(project_root),
            "message": "Onboarding state is present but malformed.",
            "recommended_command": "python3 scripts/memory.py doctor . --write-state --write-checklist",
        }

    safe_to_auto_execute = bool(step.get("safe_to_auto_execute"))
    approval_required = bool(step.get("approval_required", not safe_to_auto_execute))
    if approval_required and not approve_unsafe:
        return {
            "status": "approval_required",
            "project_root": str(project_root),
            "step": step,
            "state_updated": False,
            "artifacts_refreshed": False,
            "message": "This onboarding step is not marked safe for automatic execution.",
            "approval_reason": step.get("approval_reason"),
            "recommended_command": f"amem onboarding-execute {shlex.quote(str(project_root))} --approve-unsafe",
        }

    executed_at = datetime.now(timezone.utc).isoformat()
    command_payload = _run_onboarding_command(ctx, project_root, str(step.get("command") or ""))
    event: dict[str, object] = {
        "group": step.get("group"),
        "key": step.get("key"),
        "priority": step.get("priority"),
        "detail": step.get("detail"),
        "command": step.get("command"),
        "resolved_command": command_payload["resolved_command"],
        "verify_with": step.get("verify_with"),
        "safe_to_auto_execute": safe_to_auto_execute,
        "approval_required": approval_required,
        "approval_reason": step.get("approval_reason"),
        "approve_unsafe": approve_unsafe,
        "executed_at": executed_at,
        "execution_returncode": command_payload["returncode"],
        "execution_success": command_payload["success"],
        "verification_run": False,
        "verification_returncode": None,
        "verification_success": None,
        "verified_at": None,
        "status": "execution_failed",
    }
    if not command_payload["success"]:
        updated_state = _merge_onboarding_execution_state(state, event)
        _write_onboarding_state_file(ctx, project_root, updated_state)
        return {
            "status": "execution_failed",
            "project_root": str(project_root),
            "step": step,
            "execution": command_payload,
            "verify": None,
            "state_updated": True,
            "artifacts_refreshed": False,
            "approval_used": approve_unsafe and approval_required,
        }

    verify_payload: dict[str, object] | None = None
    if verify:
        verified_at = datetime.now(timezone.utc).isoformat()
        verify_payload = _run_onboarding_command(ctx, project_root, str(step.get("verify_with") or "amem doctor ."))
        event["verification_run"] = True
        event["resolved_verify_with"] = verify_payload["resolved_command"]
        event["verified_at"] = verified_at
        event["verification_returncode"] = verify_payload["returncode"]
        event["verification_success"] = verify_payload["success"]
        event["status"] = "verified" if verify_payload["success"] else "verification_failed"
    else:
        event["status"] = "executed"

    artifacts_refreshed = False
    written_artifacts: list[Path] = []
    if (not verify or (verify_payload and verify_payload["success"])) and refresh_artifacts:
        report = _doctor_report(ctx, str(project_root))
        if report is not None:
            written_artifacts = _write_doctor_artifacts(
                ctx,
                str(report["project_id"]),
                _report_project_root(report),
                str(report["overall"]),
                _report_grouped_checks(report),
                _result_string_list(report.get("action_sequence")),
                _report_steps(report, "runbook_steps"),
                _result_string_list(report.get("checklist")),
                write_state=True,
                write_checklist=True,
            )
            artifacts_refreshed = bool(written_artifacts)

    refreshed_state = load_onboarding_state(project_root)
    updated_state = _merge_onboarding_execution_state(refreshed_state or state, event)
    _write_onboarding_state_file(ctx, project_root, updated_state)
    return {
        "status": str(event["status"]),
        "project_root": str(project_root),
        "step": step,
        "execution": command_payload,
        "verify": verify_payload,
        "state_updated": True,
        "artifacts_refreshed": artifacts_refreshed,
        "written_artifacts": [str(path) for path in written_artifacts],
        "approval_used": approve_unsafe and approval_required,
        "next_action": onboarding_next_action(project_root),
    }


def cmd_onboarding_execute(
    ctx: AppContext,
    project_id_or_path: str = ".",
    *,
    verify: bool = True,
    approve_unsafe: bool = False,
) -> None:
    # This command is the human-facing wrapper around the execution engine, so
    # it explains approval gates and surfaces stdout/stderr from both steps.
    _project_id, project_root, _project = resolve_project_target(ctx, project_id_or_path)
    if project_root is None:
        ctx.logger.warning("onboarding_execute_skip | target=%s | reason=unknown_project_or_path", project_id_or_path)
        print(f"项目 '{project_id_or_path}' 未注册且不是有效路径。")
        print(REGISTER_HINT)
        return

    result = execute_onboarding_next_action(
        ctx,
        project_root,
        verify=verify,
        approve_unsafe=approve_unsafe,
        refresh_artifacts=True,
    )
    status = str(result.get("status"))
    if status in {"missing", "ready", "invalid", "approval_required"}:
        _print_onboarding_execute_pending(result, project_root=project_root, status=status)
        return

    step = _result_mapping(result.get("step"))
    execution = _result_mapping(result.get("execution"))
    verify_result = _result_mapping(result.get("verify"))

    _print_onboarding_execute_header(project_root, status=status)
    print(f"Step:         {step.get('group')} / {step.get('key')}")
    _print_onboarding_execution_block(execution)
    _print_onboarding_verify_block(verify_result)
    _print_onboarding_state_block(result)
    _print_onboarding_next_action(result)


def cmd_enable(ctx: AppContext, project_id_or_path: str = ".", *, full: bool = False, dry_run: bool = False, json_output: bool = False) -> int:
    return run_enable_command(
        ctx,
        project_id_or_path,
        full=full,
        dry_run=dry_run,
        json_output=json_output,
        doctor_report_fn=_doctor_report,
        doctor_command_fn=lambda hook_ctx, target: cmd_doctor(hook_ctx, target, write_state=True, write_checklist=True),
        load_state_fn=load_onboarding_state,
        merge_refactor_state_fn=_merge_refactor_followup_state,
        write_state_fn=_write_onboarding_state_file,
    )
