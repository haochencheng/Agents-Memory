from __future__ import annotations

import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from agents_memory.constants import PYTHON_BIN, REGISTER_HINT
from agents_memory.runtime import AppContext
from agents_memory.services.integration_doctor import (
    _doctor_report,
    _report_grouped_checks,
    _report_project_root,
    _report_steps,
    _result_mapping,
    _result_string_list,
    _runbook_step_from_state,
    _write_doctor_artifacts,
    _write_onboarding_state_file,
    load_onboarding_state,
    onboarding_next_action,
)
from agents_memory.services.projects import resolve_project_target


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


def _invalid_onboarding_result(project_root: Path) -> dict[str, object]:
    return {
        "status": "invalid",
        "project_root": str(project_root),
        "message": "Onboarding state is present but malformed.",
        "recommended_command": "python3 scripts/memory.py doctor . --write-state --write-checklist",
    }


def _approval_required_result(project_root: Path, step: dict[str, object]) -> dict[str, object]:
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


def _start_execution_event(step: dict[str, object], command_payload: dict[str, object], *, approve_unsafe: bool, approval_required: bool, safe_to_auto_execute: bool) -> dict[str, object]:
    return {
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
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "execution_returncode": command_payload["returncode"],
        "execution_success": command_payload["success"],
        "verification_run": False,
        "verification_returncode": None,
        "verification_success": None,
        "verified_at": None,
        "status": "execution_failed",
    }


def _execution_failure_result(
    ctx: AppContext,
    project_root: Path,
    state: dict[str, object] | None,
    step: dict[str, object],
    command_payload: dict[str, object],
    event: dict[str, object],
    *,
    approve_unsafe: bool,
    approval_required: bool,
) -> dict[str, object]:
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


def _verify_onboarding_step(ctx: AppContext, project_root: Path, step: dict[str, object], event: dict[str, object], *, verify: bool) -> dict[str, object] | None:
    if not verify:
        event["status"] = "executed"
        return None

    verify_payload = _run_onboarding_command(ctx, project_root, str(step.get("verify_with") or "amem doctor ."))
    event["verification_run"] = True
    event["resolved_verify_with"] = verify_payload["resolved_command"]
    event["verified_at"] = datetime.now(timezone.utc).isoformat()
    event["verification_returncode"] = verify_payload["returncode"]
    event["verification_success"] = verify_payload["success"]
    event["status"] = "verified" if verify_payload["success"] else "verification_failed"
    return verify_payload


def _refresh_onboarding_artifacts(ctx: AppContext, project_root: Path, *, should_refresh: bool) -> tuple[bool, list[Path]]:
    if not should_refresh:
        return False, []

    report = _doctor_report(ctx, str(project_root))
    if report is None:
        return False, []

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
    return bool(written_artifacts), written_artifacts


def _successful_execution_result(
    ctx: AppContext,
    project_root: Path,
    state: dict[str, object] | None,
    step: dict[str, object],
    command_payload: dict[str, object],
    verify_payload: dict[str, object] | None,
    event: dict[str, object],
    *,
    approve_unsafe: bool,
    approval_required: bool,
    refresh_artifacts: bool,
) -> dict[str, object]:
    artifacts_refreshed, written_artifacts = _refresh_onboarding_artifacts(
        ctx,
        project_root,
        should_refresh=(not verify_payload or bool(verify_payload["success"])) and refresh_artifacts,
    )
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


def _run_approved_onboarding_step(
    ctx: AppContext,
    project_root: Path,
    step: dict[str, object],
    state: dict[str, object] | None,
    *,
    approve_unsafe: bool,
    approval_required: bool,
    safe_to_auto_execute: bool,
    verify: bool,
    refresh_artifacts: bool,
) -> dict[str, object]:
    # Execute the approved onboarding command and verify or report the outcome.
    command_payload = _run_onboarding_command(ctx, project_root, str(step.get("command") or ""))
    event = _start_execution_event(
        step,
        command_payload,
        approve_unsafe=approve_unsafe,
        approval_required=approval_required,
        safe_to_auto_execute=safe_to_auto_execute,
    )
    if not command_payload["success"]:
        return _execution_failure_result(
            ctx, project_root, state, step, command_payload, event,
            approve_unsafe=approve_unsafe, approval_required=approval_required,
        )
    verify_payload = _verify_onboarding_step(ctx, project_root, step, event, verify=verify)
    return _successful_execution_result(
        ctx, project_root, state, step, command_payload, verify_payload, event,
        approve_unsafe=approve_unsafe, approval_required=approval_required,
        refresh_artifacts=refresh_artifacts,
    )


def execute_onboarding_next_action(
    ctx: AppContext,
    project_root: Path,
    *,
    verify: bool = True,
    approve_unsafe: bool = False,
    refresh_artifacts: bool = True,
) -> dict[str, object]:
    # Resolve the next pending onboarding step and execute or gate it.
    state = load_onboarding_state(project_root)
    action = onboarding_next_action(project_root)
    if action["status"] != "pending":
        return action

    step = _runbook_step_from_state(state or {})
    if step is None:
        return _invalid_onboarding_result(project_root)

    safe_to_auto_execute = bool(step.get("safe_to_auto_execute"))
    approval_required = bool(step.get("approval_required", not safe_to_auto_execute))
    if approval_required and not approve_unsafe:
        return _approval_required_result(project_root, step)

    return _run_approved_onboarding_step(
        ctx, project_root, step, state,
        approve_unsafe=approve_unsafe,
        approval_required=approval_required,
        safe_to_auto_execute=safe_to_auto_execute,
        verify=verify,
        refresh_artifacts=refresh_artifacts,
    )


def cmd_onboarding_execute(
    ctx: AppContext,
    project_id_or_path: str = ".",
    *,
    verify: bool = True,
    approve_unsafe: bool = False,
) -> None:
    # Execute the next pending onboarding action and print the outcome.
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