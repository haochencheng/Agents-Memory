from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from agents_memory.constants import MCP_CONFIG_NAME, PYTHON_BIN, REGISTER_HINT, VSCODE_DIRNAME
from agents_memory.integrations.agents.registry import DEFAULT_AGENT, get_agent_adapter
from agents_memory.logging_utils import log_file_update
from agents_memory.runtime import AppContext
from agents_memory.services.integration_setup import mcp_package_ready, python_ready
from agents_memory.services.projects import resolve_bridge_rel, resolve_project_target
from agents_memory.services.profiles import detect_applied_profile, load_profile, profile_agents_router_status
from agents_memory.services.validation import collect_plan_check_findings, collect_profile_check_findings, collect_refactor_watch_findings, collect_refactor_watch_hotspots


DOCTOR_GROUP_ORDER = ["Core", "Planning", "Integration", "Optional"]
DOCTOR_COMMAND = "amem doctor ."
REGISTER_COMMAND = "amem register ."
DOCTOR_REBUILD_COMMAND = "python3 scripts/memory.py doctor . --write-state --write-checklist"
INVALID_ONBOARDING_MESSAGE = "Onboarding state is present but malformed."
DOCTOR_GROUP_PRIORITY = {
    "Core": "required",
    "Planning": "required",
    "Integration": "required",
    "Optional": "recommended",
}
DOCTOR_RUNBOOK = {
    "registry": {
        "action": "Register the repository into the shared project registry so sync and doctor can reason about it.",
        "command": REGISTER_COMMAND,
        "verify_with": DOCTOR_COMMAND,
        "done_when": "`amem doctor .` shows `[OK] registry` for this project.",
        "safe_to_auto_execute": False,
        "approval_reason": "registration mutates shared project registry state and may install multiple integration files",
    },
    "active": {
        "action": "Make sure the registered project is marked active before relying on sync or governance checks.",
        "command": REGISTER_COMMAND,
        "verify_with": DOCTOR_COMMAND,
        "done_when": "`amem doctor .` shows `[OK] active`.",
        "safe_to_auto_execute": False,
        "approval_reason": "fixing active status changes shared registry metadata and should be reviewed by a human owner",
    },
    "root": {
        "action": "Repair the project root mapping so Agents-Memory resolves the correct repository path.",
        "command": REGISTER_COMMAND,
        "verify_with": DOCTOR_COMMAND,
        "done_when": "`amem doctor .` shows `[OK] root` with the expected absolute path.",
        "safe_to_auto_execute": False,
        "approval_reason": "repairing root mapping changes registry paths and can affect other automation flows",
    },
    PYTHON_BIN: {
        "action": f"Install `{PYTHON_BIN}` or expose it on PATH for runtime checks and MCP startup.",
        "command": f"{PYTHON_BIN} --version",
        "verify_with": DOCTOR_COMMAND,
        "done_when": f"`amem doctor .` shows `[OK] {PYTHON_BIN}`.",
        "safe_to_auto_execute": False,
        "approval_reason": "runtime setup may require machine-level changes outside the repository",
    },
    "mcp_package": {
        "action": "Install the MCP package into the Python environment used by Agents-Memory.",
        "command": f"{PYTHON_BIN} -m pip install mcp",
        "verify_with": DOCTOR_COMMAND,
        "done_when": "`amem doctor .` shows `[OK] mcp_package`.",
        "safe_to_auto_execute": False,
        "approval_reason": "package installation mutates the active Python environment",
    },
    "profile_manifest": {
        "action": "Apply a project profile so the repo has an explicit engineering contract.",
        "command": "amem profile-apply <profile> .",
        "verify_with": DOCTOR_COMMAND,
        "done_when": "`amem doctor .` shows `[OK] profile_manifest`.",
        "safe_to_auto_execute": False,
        "approval_reason": "profile application writes multiple managed files and requires an explicit profile choice",
    },
    "profile_consistency": {
        "action": "Repair missing or drifted profile-managed files before continuing onboarding.",
        "command": "amem profile-check .",
        "verify_with": "amem profile-check .",
        "done_when": "`amem doctor .` shows `[OK] profile_consistency`.",
        "safe_to_auto_execute": False,
        "approval_reason": "this step diagnoses drift but manual repair choices still require a human decision",
    },
    "planning_root": {
        "action": "Seed the planning workspace so specs, plans, task graphs, and validation bundles have a home.",
        "command": 'amem plan-init "<task-name>" .',
        "verify_with": DOCTOR_COMMAND,
        "done_when": "`amem doctor .` shows `[OK] planning_root`.",
        "safe_to_auto_execute": False,
        "approval_reason": "planning bootstrap requires a human task name and creates tracked planning artifacts",
    },
    "planning_bundle": {
        "action": "Repair the planning bundle so the repository has a valid spec-first execution package.",
        "command": "amem plan-check .",
        "verify_with": "amem plan-check .",
        "done_when": "`amem doctor .` shows `[OK] planning_bundle`.",
        "safe_to_auto_execute": False,
        "approval_reason": "plan-check only diagnoses issues; actual planning repairs should be reviewed before editing tracked docs",
    },
    "bridge_instruction": {
        "action": "Install the bridge instruction so agents can load shared startup context automatically.",
        "command": "amem bridge-install <project-id>",
        "verify_with": DOCTOR_COMMAND,
        "done_when": "`amem doctor .` shows `[OK] bridge_instruction`.",
        "safe_to_auto_execute": False,
        "approval_reason": "bridge installation writes tracked repository instructions and may require project-specific review",
    },
    "mcp_config": {
        "action": "Create or repair the MCP configuration so IDE agents can call Agents-Memory tools.",
        "command": "amem mcp-setup .",
        "verify_with": DOCTOR_COMMAND,
        "done_when": "`amem doctor .` shows `[OK] mcp_config`.",
        "safe_to_auto_execute": True,
        "approval_reason": "writes only local IDE MCP config under .vscode for the current project",
    },
    "copilot_activation": {
        "action": "Install repo-wide Copilot activation so the default agent loads the shared brain automatically.",
        "command": "amem copilot-setup .",
        "verify_with": DOCTOR_COMMAND,
        "done_when": "`amem doctor .` shows `[OK] copilot_activation`.",
        "safe_to_auto_execute": False,
        "approval_reason": "copilot activation writes tracked repository instructions that should be explicitly approved",
    },
    "agents_read_order": {
        "action": "Refresh the managed AGENTS.md read-order block so it references the current bridge instruction and profile-managed standards.",
        "command": "amem standards-sync .",
        "verify_with": DOCTOR_COMMAND,
        "done_when": "`amem doctor .` shows `[OK] agents_read_order`.",
        "safe_to_auto_execute": False,
        "approval_reason": "refreshing AGENTS.md updates tracked repository instructions and should be reviewed before commit",
    },
}
DOCTOR_GROUP_REMEDIATION = {
    "Core": {
        "registry": "Register the project in memory/projects.md or re-run `amem register`.",
        "active": "Mark the project active in memory/projects.md before relying on sync or doctor.",
        "root": "Fix the target path or run doctor from a valid project root.",
        PYTHON_BIN: f"Install `{PYTHON_BIN}` or make sure it is on PATH.",
        "mcp_package": "Install the `mcp` package in the Python environment used by Agents-Memory.",
        "profile_consistency": "Re-run `amem profile-check .` and repair the missing profile-managed files.",
        "profile_manifest": "Apply a profile with `amem profile-apply <profile> .` if this project should be profile-managed.",
    },
    "Planning": {
        "planning_root": "Run `amem plan-init \"<task-name>\" .` or install a profile that seeds docs/plans/README.md.",
        "planning_bundle": "Run `amem plan-check .`, then fill in or repair the missing planning bundle files.",
    },
    "Integration": {
        "bridge_instruction": "Install the bridge with `amem bridge-install <project-id>` if this repo should use bridge-based startup context.",
        "mcp_config": "Run `amem mcp-setup .` to repair or create the MCP server configuration.",
    },
    "Optional": {
        "copilot_activation": "Run `amem copilot-setup .` to add repo-wide Copilot auto-activation.",
        "agents_read_order": "Re-run `amem standards-sync .` or `amem enable . --full` so AGENTS.md references the current bridge and managed standards.",
        "refactor_watch": "Refactor flagged functions before adding more behavior, and add a short guiding comment when complex logic must remain in place.",
    },
}


def _doctor_registry_checks(project_id: str, project_root: Path, project: dict | None) -> list[tuple[str, str, str]]:
    checks: list[tuple[str, str, str]] = []
    if project:
        checks.append(("OK", "registry", f"registered as '{project.get('id', project_id)}'"))
        active = project.get("active", "true").lower() == "true"
        checks.append((("OK" if active else "FAIL"), "active", f"active={project.get('active', 'true')}"))
    else:
        checks.append(("FAIL", "registry", "project is not registered in memory/projects.md"))
    checks.append((("OK" if project_root.exists() else "FAIL"), "root", str(project_root)))
    return checks


def _doctor_bridge_check(project_root: Path, bridge_rel: str | None) -> tuple[str, str, str]:
    if not bridge_rel:
        return "INFO", "bridge_instruction", "bridge not configured for this project"
    bridge_file = project_root / bridge_rel
    bridge_status = "FAIL"
    bridge_detail = str(bridge_file)
    if bridge_file and bridge_file.exists():
        bridge_status = "OK"
    return bridge_status, "bridge_instruction", bridge_detail


def _doctor_mcp_check(ctx: AppContext, project_root: Path) -> tuple[str, str, str]:
    mcp_file = project_root / VSCODE_DIRNAME / MCP_CONFIG_NAME
    mcp_status = "FAIL"
    mcp_detail = str(mcp_file)
    if not mcp_file.exists():
        return mcp_status, "mcp_config", mcp_detail
    try:
        content = json.loads(mcp_file.read_text(encoding="utf-8"))
        server = content.get("servers", {}).get("agents-memory")
        if isinstance(server, dict):
            expected_server = str(ctx.base_dir / "scripts" / "mcp_server.py")
            if expected_server in server.get("args", []):
                return "OK", "mcp_config", f"agents-memory server configured -> {mcp_file}"
            return "WARN", "mcp_config", f"agents-memory exists but args do not include {expected_server}"
        return mcp_status, "mcp_config", f"agents-memory server entry missing in {mcp_file}"
    except Exception as exc:
        return mcp_status, "mcp_config", f"invalid JSON in {mcp_file}: {exc}"


def _doctor_agents_router_check(ctx: AppContext, project_root: Path, applied_profile_id: str | None) -> tuple[str, str, str]:
    if not applied_profile_id:
        return "INFO", "agents_read_order", "AGENTS read-order check skipped: no applied profile"

    profile = load_profile(ctx, applied_profile_id)
    is_current, detail = profile_agents_router_status(ctx, profile, project_root)
    return ("OK" if is_current else "WARN"), "agents_read_order", detail


def _doctor_runtime_checks() -> list[tuple[str, str, str]]:
    python_ok, python_detail = python_ready()
    mcp_ok, mcp_detail = mcp_package_ready()
    return [
        (("OK" if python_ok else "FAIL"), PYTHON_BIN, python_detail),
        (("OK" if mcp_ok else "FAIL"), "mcp_package", mcp_detail),
    ]


def _doctor_profile_checks(ctx: AppContext, project_root: Path) -> list[tuple[str, str, str]]:
    applied_profile_id = detect_applied_profile(project_root)
    if not applied_profile_id:
        return [("INFO", "profile_manifest", "no applied profile manifest found")]

    findings = collect_profile_check_findings(ctx, project_root, profile_id=applied_profile_id)
    profile_fail = [finding for finding in findings if finding.status == "FAIL"]
    profile_warn = [finding for finding in findings if finding.status == "WARN"]
    checks: list[tuple[str, str, str]] = [("OK", "profile_manifest", f"applied profile '{applied_profile_id}'")]
    if profile_fail:
        checks.append(("FAIL", "profile_consistency", profile_fail[0].detail))
    elif profile_warn:
        checks.append(("WARN", "profile_consistency", profile_warn[0].detail))
    else:
        checks.append(("OK", "profile_consistency", f"profile '{applied_profile_id}' consistency OK"))
    return checks


def _doctor_planning_checks(project_root: Path) -> list[tuple[str, str, str]]:
    planning_root = project_root / "docs" / "plans"
    applied_profile = detect_applied_profile(project_root)
    if not planning_root.exists():
        if applied_profile:
            return [("WARN", "planning_root", f"missing docs/plans for applied profile '{applied_profile}'")]
        return [("INFO", "planning_root", "no docs/plans directory detected")]

    findings = collect_plan_check_findings(project_root, str(project_root))
    bundle_findings = [finding for finding in findings if finding.key in {"plan_bundle", "plan_files", "plan_semantics"}]
    has_fail = any(finding.status == "FAIL" for finding in bundle_findings)
    has_warn = any(finding.status == "WARN" for finding in bundle_findings)
    bundle_count = sum(1 for finding in findings if finding.key == "plan_bundle")

    checks: list[tuple[str, str, str]] = [("OK", "planning_root", f"present: {planning_root}")]
    if has_fail:
        first_fail = next(finding for finding in bundle_findings if finding.status == "FAIL")
        checks.append(("FAIL", "planning_bundle", first_fail.detail))
    elif has_warn:
        first_warn = next(finding for finding in bundle_findings if finding.status == "WARN")
        checks.append(("WARN", "planning_bundle", first_warn.detail))
    else:
        checks.append(("OK", "planning_bundle", f"{bundle_count} planning bundle(s) passed plan-check"))
    return checks


def _doctor_refactor_watch_checks(project_root: Path) -> list[tuple[str, str, str]]:
    findings = collect_refactor_watch_findings(project_root)
    return [(finding.status, finding.key, finding.detail) for finding in findings]


def _doctor_overall(checks: list[tuple[str, str, str]]) -> str:
    required_statuses = [status for status, key, _ in checks if key not in {"agents_read_order", "copilot_activation", "profile_manifest", "refactor_watch"} and status != "INFO"]
    if not required_statuses:
        return "READY"
    if all(status == "OK" for status in required_statuses):
        return "READY"
    if any(status == "OK" for status in required_statuses):
        return "PARTIAL"
    return "NOT_READY"


def _doctor_group_name(key: str) -> str:
    if key in {"registry", "active", "root", PYTHON_BIN, "mcp_package", "profile_manifest", "profile_consistency"}:
        return "Core"
    if key in {"planning_root", "planning_bundle"}:
        return "Planning"
    if key in {"bridge_instruction", "mcp_config"}:
        return "Integration"
    return "Optional"


def _doctor_group_checks(checks: list[tuple[str, str, str]]) -> list[tuple[str, list[tuple[str, str, str]]]]:
    grouped: dict[str, list[tuple[str, str, str]]] = {name: [] for name in DOCTOR_GROUP_ORDER}
    for check in checks:
        grouped[_doctor_group_name(check[1])].append(check)
    return [(name, grouped[name]) for name in DOCTOR_GROUP_ORDER if grouped[name]]


def _doctor_group_status(group_checks: list[tuple[str, str, str]]) -> str:
    statuses = [status for status, _key, _detail in group_checks]
    if any(status == "FAIL" for status in statuses):
        return "ATTENTION"
    if any(status == "WARN" for status in statuses):
        return "WATCH"
    return "HEALTHY"


def _doctor_group_summary(group_name: str, group_checks: list[tuple[str, str, str]]) -> str:
    counts = {"OK": 0, "WARN": 0, "FAIL": 0, "INFO": 0}
    for status, _key, _detail in group_checks:
        counts[status] = counts.get(status, 0) + 1
    return f"{group_name} status={_doctor_group_status(group_checks)} (ok={counts['OK']}, warn={counts['WARN']}, fail={counts['FAIL']}, info={counts['INFO']})"


def _doctor_group_remediations(group_name: str, group_checks: list[tuple[str, str, str]]) -> list[str]:
    suggestions: list[str] = []
    seen: set[str] = set()
    remediation_map = DOCTOR_GROUP_REMEDIATION.get(group_name, {})
    for status, key, _detail in group_checks:
        if status not in {"WARN", "FAIL"}:
            continue
        suggestion = remediation_map.get(key)
        if suggestion and suggestion not in seen:
            suggestions.append(suggestion)
            seen.add(suggestion)
    return suggestions


def _doctor_action_sequence(grouped_checks: list[tuple[str, list[tuple[str, str, str]]]]) -> list[str]:
    actions: list[str] = []
    for group_name, group_checks in grouped_checks:
        remediations = _doctor_group_remediations(group_name, group_checks)
        if not remediations:
            continue
        priority = DOCTOR_GROUP_PRIORITY.get(group_name, "recommended")
        actions.append(f"{group_name} ({priority}): {'; '.join(remediations)}")
    return actions


def _doctor_runbook_step_payload(
    *,
    group_name: str,
    priority: str,
    status: str,
    key: str,
    detail: str,
    runbook: dict[str, object],
) -> dict[str, object]:
    safe_to_auto_execute = bool(runbook.get("safe_to_auto_execute", False))
    return {
        "group": group_name,
        "priority": priority,
        "key": key,
        "status": status,
        "detail": detail,
        "action": runbook["action"],
        "command": runbook["command"],
        "verify_with": runbook["verify_with"],
        "done_when": runbook["done_when"],
        "safe_to_auto_execute": safe_to_auto_execute,
        "approval_required": not safe_to_auto_execute,
        "approval_reason": runbook.get("approval_reason", "manual approval required before this onboarding action can run"),
    }


def _doctor_append_runbook_step(
    *,
    steps: list[dict[str, object]],
    seen: set[tuple[str, str]],
    group_name: str,
    priority: str,
    check: tuple[str, str, str],
) -> None:
    status, key, detail = check
    if status not in {"WARN", "FAIL"}:
        return

    runbook = DOCTOR_RUNBOOK.get(key)
    if runbook is None:
        return

    step_id = (group_name, key)
    if step_id in seen:
        return

    steps.append(
        _doctor_runbook_step_payload(
            group_name=group_name,
            priority=priority,
            status=status,
            key=key,
            detail=detail,
            runbook=runbook,
        )
    )
    seen.add(step_id)


def _doctor_attach_next_commands(steps: list[dict[str, object]]) -> list[dict[str, object]]:
    for index, step in enumerate(steps):
        step["next_command"] = steps[index + 1]["command"] if index + 1 < len(steps) else DOCTOR_COMMAND
    return steps


def _doctor_runbook_steps(grouped_checks: list[tuple[str, list[tuple[str, str, str]]]]) -> list[dict[str, object]]:
    steps: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for group_name, group_checks in grouped_checks:
        priority = DOCTOR_GROUP_PRIORITY.get(group_name, "recommended")
        for check in group_checks:
            _doctor_append_runbook_step(
                steps=steps,
                seen=seen,
                group_name=group_name,
                priority=priority,
                check=check,
            )
    return _doctor_attach_next_commands(steps)


def _doctor_bootstrap_checklist(grouped_checks: list[tuple[str, list[tuple[str, str, str]]]], runbook_steps: list[dict[str, object]]) -> list[str]:
    checklist: list[str] = []
    for group_name, group_checks in grouped_checks:
        group_status = _doctor_group_status(group_checks)
        checked = "[x]" if group_status == "HEALTHY" else "[ ]"
        checklist.append(f"{checked} {group_name} - {_doctor_group_summary(group_name, group_checks)}")
    final_checked = "[x]" if not runbook_steps else "[ ]"
    final_detail = "re-run `amem doctor .` and confirm no remaining WARN / FAIL steps" if runbook_steps else "latest `amem doctor .` already reflects the current healthy state"
    checklist.append(f"{final_checked} Final verification - {final_detail}")
    return checklist


def _doctor_recommended_step(runbook_steps: list[dict[str, object]]) -> dict[str, object] | None:
    return runbook_steps[0] if runbook_steps else None


def _doctor_required_steps_pending(runbook_steps: list[dict[str, object]]) -> bool:
    return any(step.get("priority") == "required" for step in runbook_steps)


def _doctor_group_payloads(grouped_checks: list[tuple[str, list[tuple[str, str, str]]]]) -> list[dict[str, object]]:
    groups: list[dict[str, object]] = []
    for group_name, group_checks in grouped_checks:
        groups.append(
            {
                "name": group_name,
                "status": _doctor_group_status(group_checks),
                "summary": _doctor_group_summary(group_name, group_checks),
                "checks": [{"status": status, "key": key, "detail": detail} for status, key, detail in group_checks],
            }
        )
    return groups


def _doctor_preserved_execution_metadata(existing_state: dict[str, object] | None) -> dict[str, object]:
    if not existing_state:
        return {}
    payload: dict[str, object] = {}
    for key in ("execution_history", "last_executed_action", "last_verified_action", "last_execution_status", "last_execution_at"):
        if key in existing_state:
            payload[key] = existing_state[key]
    return payload


def _doctor_refactor_followup_metadata(
    preserved_steps: list[dict[str, object]],
    preserved_bundle: dict[str, object] | None,
    *,
    runbook_steps: list[dict[str, object]],
) -> dict[str, object]:
    payload: dict[str, object] = {}
    if preserved_steps:
        payload["recommended_steps"] = preserved_steps
    if preserved_bundle is not None:
        payload["recommended_refactor_bundle"] = preserved_bundle
    if not runbook_steps and preserved_steps:
        payload.update(_recommended_step_metadata(preserved_steps[0]))
    return payload


def _doctor_state_payload(
    project_id: str,
    project_root: Path,
    overall: str,
    grouped_checks: list[tuple[str, list[tuple[str, str, str]]]],
    action_sequence: list[str],
    runbook_steps: list[dict[str, object]],
    checklist: list[str],
    existing_state: dict[str, object] | None = None,
) -> dict[str, object]:
    recommended_step = _doctor_recommended_step(runbook_steps)
    preserved_steps, preserved_bundle = _reconcile_recommended_refactor_state(existing_state, project_root)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_id": project_id,
        "project_root": str(project_root),
        "overall": overall,
        "project_bootstrap_ready": not _doctor_required_steps_pending(runbook_steps),
        "project_bootstrap_complete": not runbook_steps,
        "recommended_next_group": recommended_step["group"] if recommended_step else None,
        "recommended_next_key": recommended_step["key"] if recommended_step else None,
        "recommended_next_command": recommended_step["command"] if recommended_step else None,
        "recommended_verify_command": recommended_step["verify_with"] if recommended_step else DOCTOR_COMMAND,
        "recommended_done_when": recommended_step["done_when"] if recommended_step else "No pending onboarding steps remain.",
        "recommended_next_safe_to_auto_execute": bool(recommended_step.get("safe_to_auto_execute")) if recommended_step else False,
        "recommended_next_approval_required": bool(recommended_step.get("approval_required")) if recommended_step else False,
        "recommended_next_approval_reason": recommended_step.get("approval_reason") if recommended_step else None,
        "groups": _doctor_group_payloads(grouped_checks),
        "action_sequence": action_sequence,
        "runbook_steps": runbook_steps,
        "bootstrap_checklist": checklist,
    }
    payload.update(_doctor_preserved_execution_metadata(existing_state))
    payload.update(_doctor_refactor_followup_metadata(preserved_steps, preserved_bundle, runbook_steps=runbook_steps))
    return payload


def _doctor_checklist_markdown(
    project_id: str,
    project_root: Path,
    overall: str,
    grouped_checks: list[tuple[str, list[tuple[str, str, str]]]],
    action_sequence: list[str],
    runbook_steps: list[dict[str, object]],
    checklist: list[str],
) -> str:
    lines = ["# Bootstrap Checklist", "", f"- Project: `{project_id}`", f"- Root: `{project_root}`", f"- Overall: `{overall}`", "", "## Checklist"]
    lines.extend(f"- {item}" for item in checklist)
    if action_sequence:
        lines.extend(["", "## Action Sequence"])
        lines.extend(f"{index}. {item}" for index, item in enumerate(action_sequence, start=1))
    if runbook_steps:
        lines.extend(["", "## Onboarding Runbook"])
        for index, step in enumerate(runbook_steps, start=1):
            lines.extend([
                f"### Step {index}: {step['group']} / {step['key']}",
                f"- Priority: `{step['priority']}`",
                f"- Trigger: {step['detail']}",
                f"- Action: {step['action']}",
                f"- Command: `{step['command']}`",
                f"- Verify with: `{step['verify_with']}`",
                f"- Next command: `{step['next_command']}`",
                f"- Safe To Auto Execute: `{step['safe_to_auto_execute']}`",
                f"- Approval Required: `{step['approval_required']}`",
                f"- Approval Reason: {step['approval_reason']}",
                f"- Done when: {step['done_when']}",
                "",
            ])
    lines.extend(["## Group Health"])
    for group_name, group_checks in grouped_checks:
        lines.append(f"### {group_name}")
        lines.append(f"- Summary: {_doctor_group_summary(group_name, group_checks)}")
        for status, key, detail in group_checks:
            lines.append(f"- [{status}] `{key}` {detail}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _doctor_refactor_watch_markdown(project_id: str, project_root: Path, grouped_checks: list[tuple[str, list[tuple[str, str, str]]]]) -> str:
    refactor_findings = [(status, detail) for _group_name, group_checks in grouped_checks for status, key, detail in group_checks if key == "refactor_watch"]
    hotspots = collect_refactor_watch_hotspots(project_root)
    lines = [
        "# Refactor Watch",
        "",
        f"- Project: `{project_id}`",
        f"- Root: `{project_root}`",
        "",
        "## Purpose",
        "",
        "Track Python functions that are already high-complexity or are approaching the configured refactor thresholds.",
        "",
        "## Thresholds",
        "",
        "- Hard gate: more than 40 effective lines, more than 5 control-flow branches, nesting depth >= 4, or more than 8 local variables.",
        "- Watch zone: around 30 effective lines, 4 branches, nesting depth 3, or 6 local variables.",
        "- Complex logic should include a short guiding comment when it cannot be cleanly decomposed yet.",
        "",
        "## Workflow Entry",
        "",
        "- Primary command: `amem refactor-bundle .`",
        "- Prefer stable targeting with: `amem refactor-bundle . --token <hotspot-token>`",
        "- Fallback positional targeting: `amem refactor-bundle . --index <n>`",
        "- The command creates or refreshes `docs/plans/refactor-<slug>/` using the first current hotspot as execution context.",
        "",
        "## Hotspots",
    ]
    if not refactor_findings:
        lines.extend(["", "- No current refactor hotspots detected."])
    else:
        lines.append("")
        for index, hotspot in enumerate(hotspots, start=1):
            command = f"amem refactor-bundle . --token {hotspot.rank_token}"
            lines.append(f"{index}. [{hotspot.status}] `{hotspot.identifier}` line={hotspot.line} metrics=(lines={hotspot.effective_lines}, branches={hotspot.branches}, nesting={hotspot.nesting}, locals={hotspot.local_vars})")
            lines.append(f"   - token: `{hotspot.rank_token}`")
            lines.append(f"   - issues: `{', '.join(hotspot.issues)}`")
            lines.append(f"   - bundle command: `{command}`")
        extra_findings = refactor_findings[len(hotspots):]
        for index, (status, detail) in enumerate(extra_findings, start=len(hotspots) + 1):
            lines.append(f"{index}. [{status}] {detail}")
    lines.extend([
        "",
        "## Suggested Action",
        "",
        "1. Run `amem refactor-bundle .` to materialize the first hotspot into an executable planning bundle.",
        "2. If a hotspot cannot be split yet, add a guiding comment that explains the main decision path and risk boundaries.",
        "3. Re-run `amem doctor .` after the change and confirm `refactor_watch` findings shrink or disappear.",
    ])
    return "\n".join(lines).rstrip() + "\n"


def onboarding_state_path(project_root: Path) -> Path:
    return project_root / ".agents-memory" / "onboarding-state.json"


def load_onboarding_state(project_root: Path) -> dict[str, object] | None:
    state_path = onboarding_state_path(project_root)
    if not state_path.exists():
        return None
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _state_steps(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _state_pending_steps(state: dict[str, object]) -> list[dict[str, object]]:
    return _state_steps(state.get("runbook_steps"))


def _state_recommended_steps(state: dict[str, object]) -> list[dict[str, object]]:
    return _state_steps(state.get("recommended_steps"))


def _result_mapping(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _result_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _report_project_root(report: dict[str, object]) -> Path:
    return Path(str(report.get("project_root") or "."))


def _report_grouped_checks(report: dict[str, object]) -> list[tuple[str, list[tuple[str, str, str]]]]:
    raw_groups = report.get("grouped_checks")
    if not isinstance(raw_groups, list):
        return []
    grouped_checks: list[tuple[str, list[tuple[str, str, str]]]] = []
    for item in raw_groups:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            continue
        group_name, raw_checks = item
        if not isinstance(group_name, str) or not isinstance(raw_checks, list):
            continue
        checks: list[tuple[str, str, str]] = []
        for check in raw_checks:
            if not isinstance(check, (list, tuple)) or len(check) != 3:
                continue
            status, key, detail = check
            checks.append((str(status), str(key), str(detail)))
        grouped_checks.append((group_name, checks))
    return grouped_checks


def _report_steps(report: dict[str, object], key: str) -> list[dict[str, object]]:
    return _state_steps(report.get(key))


def _print_doctor_header(*, project_id: str, project_root: Path, overall: str) -> None:
    print("\n=== Agents-Memory Doctor ===")
    print(f"Project: {project_id}")
    print(f"Root:    {project_root}")
    print(f"Overall: {overall}\n")


def _print_doctor_groups(grouped_checks: list[tuple[str, list[tuple[str, str, str]]]]) -> None:
    for group_name, group_checks in grouped_checks:
        print(f"{group_name}:")
        print(f"Summary: {_doctor_group_summary(group_name, group_checks)}")
        for status, key, detail in group_checks:
            print(f"[{status:<4}] {key:<18} {detail}")
        remediations = _doctor_group_remediations(group_name, group_checks)
        if remediations:
            print("Remediation:")
            for item in remediations:
                print(f"- {item}")
        print()


def _print_doctor_action_sequence(action_sequence: list[str]) -> None:
    if not action_sequence:
        return
    print("Action Sequence:")
    for index, action in enumerate(action_sequence, start=1):
        print(f"{index}. {action}")
    print()


def _print_doctor_runbook(runbook_steps: list[dict[str, object]]) -> None:
    if not runbook_steps:
        return
    print("Onboarding Runbook:")
    for index, step in enumerate(runbook_steps, start=1):
        print(f"{index}. {step['group']} / {step['key']} [{step['priority']}]")
        print(f"   Trigger: {step['detail']}")
        print(f"   Action: {step['action']}")
        print(f"   Command: {step['command']}")
        print(f"   Verify with: {step['verify_with']}")
        print(f"   Next command: {step['next_command']}")
        print(f"   Safe to auto execute: {step['safe_to_auto_execute']}")
        print(f"   Approval required: {step['approval_required']}")
        print(f"   Approval reason: {step['approval_reason']}")
        print(f"   Done when: {step['done_when']}")
    print()


def _print_doctor_checklist(checklist: list[str]) -> None:
    if not checklist:
        return
    print("Project Bootstrap Checklist:")
    for item in checklist:
        print(f"- {item}")
    print()


def _print_doctor_exported_artifacts(written_artifacts: list[Path]) -> None:
    if not written_artifacts:
        return
    print("Exported Artifacts:")
    for path in written_artifacts:
        print(f"- {path}")
    print()


def _print_doctor_next_steps(*, ctx: AppContext, overall: str, project_id: str) -> None:
    print("\nNext:")
    if overall == "READY":
        print("1. 在该项目的 VS Code Agent/Chat 面板中调用 memory_get_index 进行最终运行时验证")
        print(f"2. 如需观察后续接入动作日志，执行: tail -f {ctx.base_dir / 'logs' / 'agents-memory.log'}")
    else:
        print("1. 先修复上面的 FAIL / WARN 项")
        print(f"2. 修复后重新运行: amem doctor {project_id}")


def _recommended_step_metadata(step: dict[str, object]) -> dict[str, object]:
    return {
        "recommended_next_group": step.get("group"),
        "recommended_next_key": step.get("key"),
        "recommended_next_command": step.get("command"),
        "recommended_verify_command": step.get("verify_with") or DOCTOR_COMMAND,
        "recommended_done_when": step.get("done_when") or "No pending onboarding steps remain.",
        "recommended_next_safe_to_auto_execute": bool(step.get("safe_to_auto_execute")),
        "recommended_next_approval_required": bool(step.get("approval_required")),
        "recommended_next_approval_reason": step.get("approval_reason"),
    }


def _active_refactor_hotspot_keys(project_root: Path) -> tuple[set[str], set[str]]:
    hotspots = collect_refactor_watch_hotspots(project_root)
    active_identifiers = {hotspot.identifier for hotspot in hotspots}
    active_tokens = {hotspot.rank_token for hotspot in hotspots}
    return active_identifiers, active_tokens


def _refactor_payload_matches_active_hotspot(
    hotspot_payload: object,
    *,
    active_identifiers: set[str],
    active_tokens: set[str],
) -> bool:
    if not isinstance(hotspot_payload, dict):
        return False
    identifier = hotspot_payload.get("identifier")
    token = hotspot_payload.get("rank_token")
    return bool(token in active_tokens or identifier in active_identifiers)


def _preserved_recommended_refactor_steps(
    existing_state: dict[str, object],
    *,
    active_identifiers: set[str],
    active_tokens: set[str],
) -> list[dict[str, object]]:
    preserved_steps: list[dict[str, object]] = []
    for step in _state_recommended_steps(existing_state):
        if step.get("key") != "refactor_bundle":
            preserved_steps.append(step)
            continue
        if _refactor_payload_matches_active_hotspot(
            step.get("hotspot"),
            active_identifiers=active_identifiers,
            active_tokens=active_tokens,
        ):
            preserved_steps.append(step)
    return preserved_steps


def _preserved_recommended_refactor_bundle(
    existing_state: dict[str, object],
    *,
    active_identifiers: set[str],
    active_tokens: set[str],
) -> dict[str, object] | None:
    bundle = existing_state.get("recommended_refactor_bundle")
    if not isinstance(bundle, dict):
        return None
    if _refactor_payload_matches_active_hotspot(
        bundle.get("hotspot"),
        active_identifiers=active_identifiers,
        active_tokens=active_tokens,
    ):
        return bundle
    return None


def _reconcile_recommended_refactor_state(existing_state: dict[str, object] | None, project_root: Path) -> tuple[list[dict[str, object]], dict[str, object] | None]:
    if existing_state is None:
        return [], None

    active_identifiers, active_tokens = _active_refactor_hotspot_keys(project_root)
    if not active_identifiers:
        return [step for step in _state_recommended_steps(existing_state) if step.get("key") != "refactor_bundle"], None

    return (
        _preserved_recommended_refactor_steps(
            existing_state,
            active_identifiers=active_identifiers,
            active_tokens=active_tokens,
        ),
        _preserved_recommended_refactor_bundle(
            existing_state,
            active_identifiers=active_identifiers,
            active_tokens=active_tokens,
        ),
    )


def _runbook_step_from_state(state: dict[str, object]) -> dict[str, object] | None:
    pending_steps = _state_pending_steps(state)
    if pending_steps:
        return pending_steps[0]
    recommended_steps = _state_recommended_steps(state)
    if recommended_steps:
        return recommended_steps[0]
    return None


def _write_onboarding_state_file(ctx: AppContext, project_root: Path, state: dict[str, object]) -> Path:
    state_path = onboarding_state_path(project_root)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log_file_update(ctx.logger, action="write_onboarding_state", path=state_path, detail=f"project_root={project_root}")
    return state_path


def _doctor_report(ctx: AppContext, project_id_or_path: str) -> dict[str, object] | None:
    project_id, project_root, project = resolve_project_target(ctx, project_id_or_path)
    ctx.logger.info("doctor_start | target=%s | resolved_project_id=%s | project_root=%s", project_id_or_path, project_id, project_root)
    if project_root is None:
        return None

    bridge_rel = resolve_bridge_rel(project)
    checks: list[tuple[str, str, str]] = []
    checks.extend(_doctor_registry_checks(project_id, project_root, project))
    checks.append(_doctor_bridge_check(project_root, bridge_rel))

    copilot_adapter = get_agent_adapter(DEFAULT_AGENT)
    if copilot_adapter is not None:
        copilot_check = copilot_adapter.doctor(ctx, project_root, project_id)
        if copilot_check:
            checks.append(copilot_check)
    checks.append(_doctor_mcp_check(ctx, project_root))
    checks.extend(_doctor_runtime_checks())

    if not bridge_rel:
        checks.append(("INFO", "agents_read_order", "bridge not configured; AGENTS read order check skipped"))
    else:
        checks.append(_doctor_agents_router_check(ctx, project_root, detect_applied_profile(project_root)))
    checks.extend(_doctor_profile_checks(ctx, project_root))
    checks.extend(_doctor_planning_checks(project_root))
    checks.extend(_doctor_refactor_watch_checks(project_root))

    grouped_checks = _doctor_group_checks(checks)
    runbook_steps = _doctor_runbook_steps(grouped_checks)
    action_sequence = _doctor_action_sequence(grouped_checks)
    checklist = _doctor_bootstrap_checklist(grouped_checks, runbook_steps)
    overall = _doctor_overall(checks)
    return {
        "project_id": project_id,
        "project_root": project_root,
        "project": project,
        "overall": overall,
        "checks": checks,
        "grouped_checks": grouped_checks,
        "action_sequence": action_sequence,
        "runbook_steps": runbook_steps,
        "checklist": checklist,
    }


def onboarding_next_action(project_root: Path) -> dict[str, object]:
    state = load_onboarding_state(project_root)
    if state is None:
        return {
            "status": "missing",
            "project_root": str(project_root),
            "message": "No onboarding state found for this project.",
            "recommended_command": DOCTOR_REBUILD_COMMAND,
        }

    runbook_steps = state.get("runbook_steps") or []
    recommended_steps = state.get("recommended_steps") or []
    if runbook_steps and not isinstance(runbook_steps, list):
        return {
            "status": "invalid",
            "project_root": str(project_root),
            "message": INVALID_ONBOARDING_MESSAGE,
            "recommended_command": DOCTOR_REBUILD_COMMAND,
        }
    if recommended_steps and not isinstance(recommended_steps, list):
        return {
            "status": "invalid",
            "project_root": str(project_root),
            "message": INVALID_ONBOARDING_MESSAGE,
            "recommended_command": DOCTOR_REBUILD_COMMAND,
        }
    first_step = _runbook_step_from_state(state)
    if (isinstance(runbook_steps, list) and runbook_steps and first_step is None) or (isinstance(recommended_steps, list) and recommended_steps and first_step is None):
        return {
            "status": "invalid",
            "project_root": str(project_root),
            "message": INVALID_ONBOARDING_MESSAGE,
            "recommended_command": DOCTOR_REBUILD_COMMAND,
        }
    if first_step is None:
        return {
            "status": "ready",
            "project_root": str(project_root),
            "project_bootstrap_ready": bool(state.get("project_bootstrap_ready")),
            "project_bootstrap_complete": bool(state.get("project_bootstrap_complete")),
            "message": "No pending onboarding action. Continue with normal implementation flow.",
            "recommended_command": None,
            "verify_with": state.get("recommended_verify_command") or DOCTOR_COMMAND,
        }

    blocking = not bool(state.get("project_bootstrap_ready", False))
    return {
        "status": "pending",
        "project_root": str(project_root),
        "project_bootstrap_ready": bool(state.get("project_bootstrap_ready")),
        "project_bootstrap_complete": bool(state.get("project_bootstrap_complete")),
        "blocking": blocking,
        "step_source": "runbook" if _state_pending_steps(state) else "recommended",
        "group": first_step.get("group"),
        "key": first_step.get("key"),
        "priority": first_step.get("priority"),
        "command": first_step.get("command"),
        "verify_with": first_step.get("verify_with"),
        "done_when": first_step.get("done_when"),
        "next_command": first_step.get("next_command"),
        "safe_to_auto_execute": bool(first_step.get("safe_to_auto_execute")),
        "approval_required": bool(first_step.get("approval_required")),
        "approval_reason": first_step.get("approval_reason"),
        "bundle_path": first_step.get("bundle_path"),
        "hotspot": first_step.get("hotspot"),
        "message": "Complete this onboarding action before deep work." if blocking else "Recommended onboarding follow-up is available.",
    }


def _write_doctor_artifacts(
    ctx: AppContext,
    project_id: str,
    project_root: Path,
    overall: str,
    grouped_checks: list[tuple[str, list[tuple[str, str, str]]]],
    action_sequence: list[str],
    runbook_steps: list[dict[str, object]],
    checklist: list[str],
    *,
    write_state: bool,
    write_checklist: bool,
) -> list[Path]:
    written: list[Path] = []
    existing_state = load_onboarding_state(project_root) if write_state else None
    if write_checklist:
        checklist_path = project_root / "docs" / "plans" / "bootstrap-checklist.md"
        checklist_path.parent.mkdir(parents=True, exist_ok=True)
        checklist_path.write_text(_doctor_checklist_markdown(project_id, project_root, overall, grouped_checks, action_sequence, runbook_steps, checklist), encoding="utf-8")
        log_file_update(ctx.logger, action="write_doctor_checklist", path=checklist_path, detail=f"project_id={project_id};overall={overall}")
        written.append(checklist_path)

        refactor_watch_path = project_root / "docs" / "plans" / "refactor-watch.md"
        refactor_watch_path.parent.mkdir(parents=True, exist_ok=True)
        refactor_watch_path.write_text(_doctor_refactor_watch_markdown(project_id, project_root, grouped_checks), encoding="utf-8")
        log_file_update(ctx.logger, action="write_refactor_watch", path=refactor_watch_path, detail=f"project_id={project_id};overall={overall}")
        written.append(refactor_watch_path)
    if write_state:
        state_path = project_root / ".agents-memory" / "onboarding-state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(_doctor_state_payload(project_id, project_root, overall, grouped_checks, action_sequence, runbook_steps, checklist, existing_state=existing_state), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        log_file_update(ctx.logger, action="write_doctor_state", path=state_path, detail=f"project_id={project_id};overall={overall}")
        written.append(state_path)
    return written


def cmd_doctor(
    ctx: AppContext,
    project_id_or_path: str = ".",
    write_state: bool = False,
    write_checklist: bool = False,
) -> None:
    report = _doctor_report(ctx, project_id_or_path)
    if report is None:
        ctx.logger.warning("doctor_failed | target=%s | reason=unknown_project_or_path", project_id_or_path)
        print(f"项目 '{project_id_or_path}' 未注册，且不是有效目录。")
        print(REGISTER_HINT)
        return
    project_id = str(report["project_id"])
    project_root = _report_project_root(report)
    overall = str(report["overall"])
    grouped_checks = _report_grouped_checks(report)
    action_sequence = _result_string_list(report.get("action_sequence"))
    runbook_steps = _report_steps(report, "runbook_steps")
    checklist = _result_string_list(report.get("checklist"))

    _print_doctor_header(project_id=project_id, project_root=project_root, overall=overall)
    _print_doctor_groups(grouped_checks)
    _print_doctor_action_sequence(action_sequence)
    _print_doctor_runbook(runbook_steps)
    _print_doctor_checklist(checklist)

    written_artifacts = _write_doctor_artifacts(
        ctx,
        project_id,
        project_root,
        overall,
        grouped_checks,
        action_sequence,
        runbook_steps,
        checklist,
        write_state=write_state,
        write_checklist=write_checklist,
    )
    _print_doctor_exported_artifacts(written_artifacts)
    _print_doctor_next_steps(ctx=ctx, overall=overall, project_id=project_id)
    ctx.logger.info("doctor_complete | project_id=%s | project_root=%s | overall=%s", project_id, project_root, overall)