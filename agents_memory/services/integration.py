from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from agents_memory.constants import (
    BRIDGE_TEMPLATE_NAME,
    COPILOT_INSTRUCTIONS_REL,
    DEFAULT_BRIDGE_INSTRUCTION_REL,
    MCP_CONFIG_NAME,
    PYTHON_BIN,
    REGISTER_HINT,
    VSCODE_DIRNAME,
)
from agents_memory.integrations.agents.registry import DEFAULT_AGENT, get_agent_adapter, list_agent_adapters
from agents_memory.logging_utils import log_file_update
from agents_memory.runtime import AppContext
from agents_memory.services.projects import (
    append_project_entry,
    detect_domains,
    detect_instruction_files,
    detect_project_id,
    parse_projects,
    project_agents_reference_exists,
    project_already_registered,
    resolve_bridge_rel,
    resolve_project_target,
)
from agents_memory.services.profiles import apply_profile, detect_applied_profile, load_profile
from agents_memory.services.profiles import PROFILE_MANIFEST_REL, expected_profile_paths
from agents_memory.services.records import collect_errors
from agents_memory.services.validation import collect_plan_check_findings, collect_profile_check_findings, collect_refactor_watch_findings, collect_refactor_watch_hotspots


DOCTOR_GROUP_ORDER = ["Core", "Planning", "Integration", "Optional"]
DOCTOR_GROUP_PRIORITY = {
    "Core": "required",
    "Planning": "required",
    "Integration": "required",
    "Optional": "recommended",
}
DOCTOR_RUNBOOK = {
    "registry": {
        "action": "Register the repository into the shared project registry so sync and doctor can reason about it.",
        "command": "amem register .",
        "verify_with": "amem doctor .",
        "done_when": "`amem doctor .` shows `[OK] registry` for this project.",
        "safe_to_auto_execute": False,
        "approval_reason": "registration mutates shared project registry state and may install multiple integration files",
    },
    "active": {
        "action": "Make sure the registered project is marked active before relying on sync or governance checks.",
        "command": "amem register .",
        "verify_with": "amem doctor .",
        "done_when": "`amem doctor .` shows `[OK] active`.",
        "safe_to_auto_execute": False,
        "approval_reason": "fixing active status changes shared registry metadata and should be reviewed by a human owner",
    },
    "root": {
        "action": "Repair the project root mapping so Agents-Memory resolves the correct repository path.",
        "command": "amem register .",
        "verify_with": "amem doctor .",
        "done_when": "`amem doctor .` shows `[OK] root` with the expected absolute path.",
        "safe_to_auto_execute": False,
        "approval_reason": "repairing root mapping changes registry paths and can affect other automation flows",
    },
    PYTHON_BIN: {
        "action": f"Install `{PYTHON_BIN}` or expose it on PATH for runtime checks and MCP startup.",
        "command": f"{PYTHON_BIN} --version",
        "verify_with": "amem doctor .",
        "done_when": f"`amem doctor .` shows `[OK] {PYTHON_BIN}`.",
        "safe_to_auto_execute": False,
        "approval_reason": "runtime setup may require machine-level changes outside the repository",
    },
    "mcp_package": {
        "action": "Install the MCP package into the Python environment used by Agents-Memory.",
        "command": f"{PYTHON_BIN} -m pip install mcp",
        "verify_with": "amem doctor .",
        "done_when": "`amem doctor .` shows `[OK] mcp_package`.",
        "safe_to_auto_execute": False,
        "approval_reason": "package installation mutates the active Python environment",
    },
    "profile_manifest": {
        "action": "Apply a project profile so the repo has an explicit engineering contract.",
        "command": "amem profile-apply <profile> .",
        "verify_with": "amem doctor .",
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
        "verify_with": "amem doctor .",
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
        "verify_with": "amem doctor .",
        "done_when": "`amem doctor .` shows `[OK] bridge_instruction`.",
        "safe_to_auto_execute": False,
        "approval_reason": "bridge installation writes tracked repository instructions and may require project-specific review",
    },
    "mcp_config": {
        "action": "Create or repair the MCP configuration so IDE agents can call Agents-Memory tools.",
        "command": "amem mcp-setup .",
        "verify_with": "amem doctor .",
        "done_when": "`amem doctor .` shows `[OK] mcp_config`.",
        "safe_to_auto_execute": True,
        "approval_reason": "writes only local IDE MCP config under .vscode for the current project",
    },
    "copilot_activation": {
        "action": "Install repo-wide Copilot activation so the default agent loads the shared brain automatically.",
        "command": "amem copilot-setup .",
        "verify_with": "amem doctor .",
        "done_when": "`amem doctor .` shows `[OK] copilot_activation`.",
        "safe_to_auto_execute": False,
        "approval_reason": "copilot activation writes tracked repository instructions that should be explicitly approved",
    },
    "agents_read_order": {
        "action": "Add the bridge reference to AGENTS.md or docs/AGENTS.md so humans and agents share the same startup order.",
        "command": 'rg -n "agents-memory-bridge" AGENTS.md docs/AGENTS.md',
        "verify_with": "amem doctor .",
        "done_when": "`amem doctor .` shows `[INFO] agents_read_order bridge referenced in AGENTS/docs/AGENTS`.",
        "safe_to_auto_execute": False,
        "approval_reason": "the current command is diagnostic only; updating AGENTS read order should be a human-reviewed doc edit",
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
        "agents_read_order": "Reference the bridge in AGENTS.md or docs/AGENTS.md if you want explicit read-order guidance.",
        "refactor_watch": "Refactor flagged functions before adding more behavior, and add a short guiding comment when complex logic must remain in place.",
    },
}


def render_bridge_instruction(ctx: AppContext, project_id: str) -> str:
    template_path = ctx.templates_dir / BRIDGE_TEMPLATE_NAME
    if not template_path.exists():
        raise FileNotFoundError(f"Bridge template not found: {template_path}")
    content = template_path.read_text(encoding="utf-8")
    return content.replace("{{PROJECT_ID}}", project_id).replace("{{AGENTS_MEMORY_ROOT}}", str(ctx.base_dir))


def extract_rule_text(filepath: Path) -> str:
    lines = filepath.read_text(encoding="utf-8").splitlines()
    in_rule = False
    rule_lines: list[str] = []
    for line in lines:
        if line.strip() == "## 提炼规则":
            in_rule = True
            continue
        if in_rule:
            if line.startswith("## "):
                break
            if line.strip() and not line.strip().startswith("<!--"):
                rule_lines.append(line.strip())
    return " ".join(rule_lines).strip()


def cmd_sync(ctx: AppContext) -> None:
    # Sync walks promoted records against every registered project because the
    # final write target depends on both the record metadata and the registry.
    promoted = collect_errors(ctx, status_filter=["promoted"])
    ctx.logger.info("sync_start | promoted=%s", len(promoted))
    if not promoted:
        ctx.logger.info("sync_skip | reason=no_promoted_records")
        print("No promoted records to sync.")
        return

    projects = parse_projects(ctx)
    if not projects:
        ctx.logger.warning("sync_skip | reason=no_registered_projects")
        print("No projects registered. See memory/projects.md")
        return

    synced = 0
    skipped = 0
    for record in promoted:
        raw_path = record.get("promoted_to", "").strip('"').strip("'")
        if not raw_path:
            continue
        rel_path = re.sub(r"\s*\(.*\)\s*$", "", raw_path).strip()
        abs_target: Path | None = None
        for project in projects:
            root = project.get("root", "").strip()
            if not root:
                continue
            candidate = Path(root) / rel_path
            if candidate.exists():
                abs_target = candidate
                break

        record_id = record.get("id", "unknown")
        if abs_target is None:
            ctx.logger.warning("sync_target_missing | record_id=%s | target=%s", record_id, rel_path)
            print(f"  ⚠  [{record_id}] target not found: {rel_path}")
            skipped += 1
            continue

        target_content = abs_target.read_text(encoding="utf-8")
        if record_id in target_content:
            ctx.logger.info("sync_skip | record_id=%s | reason=already_synced | target=%s", record_id, abs_target)
            print(f"  ✓  [{record_id}] already synced → {abs_target.name}")
            skipped += 1
            continue

        rule_text = extract_rule_text(Path(record["_file"]))
        if not rule_text:
            ctx.logger.warning("sync_skip | record_id=%s | reason=no_rule_text", record_id)
            print(f"  ⚠  [{record_id}] no rule text found, skipping")
            skipped += 1
            continue

        gotcha_entry = f"\n- **[`{record_id}`]** {rule_text}\n  <!-- auto-synced from agents-memory -->"
        if "## ⚠️ Gotchas" in target_content:
            target_content = target_content.replace("## ⚠️ Gotchas", f"## ⚠️ Gotchas\n{gotcha_entry}", 1)
        else:
            target_content += f"\n\n## ⚠️ Gotchas\n{gotcha_entry}\n"

        abs_target.write_text(target_content, encoding="utf-8")
        log_file_update(ctx.logger, action="sync_rule", path=abs_target, detail=f"record_id={record_id}")
        print(f"  ✅ [{record_id}] synced → {abs_target}")
        synced += 1

    ctx.logger.info("sync_complete | synced=%s | skipped=%s", synced, skipped)
    print(f"\nSync complete: {synced} synced, {skipped} skipped.")


def cmd_bridge_install(ctx: AppContext, project_id: str) -> None:
    projects = parse_projects(ctx)
    project = next((item for item in projects if item["id"] == project_id), None)
    if project is None:
        ctx.logger.warning("bridge_install_skip | project_id=%s | reason=project_not_registered", project_id)
        print(f"Project '{project_id}' not registered. Add it to memory/projects.md first.")
        return

    template_path = ctx.templates_dir / BRIDGE_TEMPLATE_NAME
    if not template_path.exists():
        ctx.logger.warning("bridge_install_skip | project_id=%s | reason=template_missing | template=%s", project_id, template_path)
        print(f"Bridge template not found: {template_path}")
        return

    root = project.get("root", "").strip()
    bridge_rel = resolve_bridge_rel(project)
    if not root or not bridge_rel:
        ctx.logger.warning("bridge_install_skip | project_id=%s | reason=missing_registry_fields", project_id)
        print(f"Missing 'root' or 'bridge_instruction' in project registry for '{project_id}'.")
        return

    destination = Path(root) / bridge_rel
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        ctx.logger.info("bridge_install_skip | project_id=%s | reason=already_installed | path=%s", project_id, destination)
        print(f"Already installed: {destination}")
        print("Delete the file manually if you want to reinstall.")
        return

    destination.write_text(render_bridge_instruction(ctx, project_id), encoding="utf-8")
    log_file_update(ctx.logger, action="install_bridge", path=destination, detail=f"project_id={project_id}")
    print(f"✅ Bridge instruction installed → {destination}")
    print(f"Next: add it to {root}/AGENTS.md read-order or .github/instructions/ references.")


def cmd_agent_list() -> None:
    print("\n=== Agent Adapters ===\n")
    for adapter in list_agent_adapters():
        status = "ready" if adapter.supported else "scaffold"
        print(f"- {adapter.name:<16} {status:<8} {adapter.display_name}")


def install_agent_adapter(ctx: AppContext, agent_name: str, project_root: Path, project_id: str) -> None:
    adapter = get_agent_adapter(agent_name)
    if adapter is None:
        print(f"Unknown agent adapter: {agent_name}")
        print("Run `amem agent-list` to see available adapters.")
        return
    result = adapter.install(ctx, project_root, project_id)
    icon = "✅" if result.status in {"created", "updated", "merged", "unchanged"} else "ℹ️"
    print(f"  {icon} {result.message}")


def cmd_agent_setup(ctx: AppContext, agent_name: str, project_id_or_path: str = ".") -> None:
    project_id, project_root, _project = resolve_project_target(ctx, project_id_or_path)
    if project_root is None:
        ctx.logger.warning("agent_setup_skip | agent=%s | target=%s | reason=unknown_project_or_path", agent_name, project_id_or_path)
        print(f"项目 '{project_id_or_path}' 未注册且不是有效路径。")
        print(REGISTER_HINT)
        return
    ctx.logger.info("agent_setup_start | agent=%s | target=%s | project_id=%s | project_root=%s", agent_name, project_id_or_path, project_id, project_root)
    print(f"\n🤖 安装 agent adapter: {agent_name} → {project_root}")
    install_agent_adapter(ctx, agent_name, project_root, project_id)


def cmd_copilot_setup(ctx: AppContext, project_id_or_path: str = ".") -> None:
    cmd_agent_setup(ctx, DEFAULT_AGENT, project_id_or_path)
    print()
    print("验证方式：在该项目的 VS Code Copilot Chat / Agent 面板中输入：")
    print("  先调用 memory_get_index()，再告诉我当前热区中最重要的规则。")


def python_ready() -> tuple[bool, str]:
    python_bin = shutil.which(PYTHON_BIN)
    if not python_bin:
        return False, f"{PYTHON_BIN} not found in PATH"
    return True, python_bin


def mcp_package_ready() -> tuple[bool, str]:
    python_bin = shutil.which(PYTHON_BIN)
    if not python_bin:
        return False, f"{PYTHON_BIN} not found in PATH"
    result = subprocess.run([python_bin, "-c", "from mcp.server.fastmcp import FastMCP"], capture_output=True, text=True)
    if result.returncode == 0:
        return True, "mcp import OK"
    stderr = (result.stderr or result.stdout or "import failed").strip().splitlines()[0]
    return False, stderr


def write_vscode_mcp_json(ctx: AppContext, project_root: Path) -> bool:
    vscode_dir = project_root / VSCODE_DIRNAME
    mcp_file = vscode_dir / MCP_CONFIG_NAME
    server_entry = {
        "type": "stdio",
        "command": PYTHON_BIN,
        "args": [str(ctx.base_dir / "scripts" / "mcp_server.py")],
        "env": {},
    }
    if mcp_file.exists():
        try:
            existing = json.loads(mcp_file.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
        if "agents-memory" in existing.get("servers", {}):
            ctx.logger.info("mcp_file_skip | path=%s | reason=already_contains_server", mcp_file)
            print(f"  已存在: {mcp_file}")
            return False
        existing.setdefault("servers", {})["agents-memory"] = server_entry
        mcp_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        log_file_update(ctx.logger, action="merge_mcp_config", path=mcp_file, detail=f"project_root={project_root}")
        print(f"  ✅ 已合并写入 agents-memory server 条目 → {mcp_file}")
        return True

    vscode_dir.mkdir(exist_ok=True)
    config = {"servers": {"agents-memory": server_entry}}
    mcp_file.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log_file_update(ctx.logger, action="write_mcp_config", path=mcp_file, detail=f"project_root={project_root}")
    print(f"  ✅ 已写入 {mcp_file}")
    return True


def cmd_mcp_setup(ctx: AppContext, project_id_or_path: str = ".") -> None:
    _, project_root, _ = resolve_project_target(ctx, project_id_or_path)
    if project_root is None:
        ctx.logger.warning("mcp_setup_skip | target=%s | reason=unknown_project_or_path", project_id_or_path)
        print(f"项目 '{project_id_or_path}' 未注册且不是有效路径。")
        print(REGISTER_HINT)
        return
    ctx.logger.info("mcp_setup_start | target=%s | project_root=%s", project_id_or_path, project_root)
    print(f"\n🛠  写入 .vscode/mcp.json → {project_root}")
    write_vscode_mcp_json(ctx, project_root)
    print()
    print("验证方式：在该项目的 VS Code Agent/Chat 面板中输入：")
    print("  请调用 memory_get_index 工具，告诉我当前有多少条错误记录。")


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
    return (
        f"{group_name} status={_doctor_group_status(group_checks)} "
        f"(ok={counts['OK']}, warn={counts['WARN']}, fail={counts['FAIL']}, info={counts['INFO']})"
    )


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


def _doctor_runbook_steps(grouped_checks: list[tuple[str, list[tuple[str, str, str]]]]) -> list[dict[str, object]]:
    steps: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for group_name, group_checks in grouped_checks:
        priority = DOCTOR_GROUP_PRIORITY.get(group_name, "recommended")
        for status, key, detail in group_checks:
            if status not in {"WARN", "FAIL"}:
                continue
            runbook = DOCTOR_RUNBOOK.get(key)
            if runbook is None:
                continue
            step_id = (group_name, key)
            if step_id in seen:
                continue
            steps.append(
                {
                    "group": group_name,
                    "priority": priority,
                    "key": key,
                    "status": status,
                    "detail": detail,
                    "action": runbook["action"],
                    "command": runbook["command"],
                    "verify_with": runbook["verify_with"],
                    "done_when": runbook["done_when"],
                    "safe_to_auto_execute": bool(runbook.get("safe_to_auto_execute", False)),
                    "approval_required": not bool(runbook.get("safe_to_auto_execute", False)),
                    "approval_reason": runbook.get("approval_reason", "manual approval required before this onboarding action can run"),
                }
            )
            seen.add(step_id)
    for index, step in enumerate(steps):
        if index + 1 < len(steps):
            step["next_command"] = steps[index + 1]["command"]
        else:
            step["next_command"] = "amem doctor ."
    return steps


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
                "checks": [
                    {"status": status, "key": key, "detail": detail}
                    for status, key, detail in group_checks
                ],
            }
        )
    return groups


def _doctor_preserved_execution_metadata(existing_state: dict[str, object] | None) -> dict[str, object]:
    if not existing_state:
        return {}

    payload: dict[str, object] = {}
    for key in (
        "execution_history",
        "last_executed_action",
        "last_verified_action",
        "last_execution_status",
        "last_execution_at",
    ):
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
        "recommended_verify_command": recommended_step["verify_with"] if recommended_step else "amem doctor .",
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
    payload.update(
        _doctor_refactor_followup_metadata(
            preserved_steps,
            preserved_bundle,
            runbook_steps=runbook_steps,
        )
    )
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
    lines = [
        "# Bootstrap Checklist",
        "",
        f"- Project: `{project_id}`",
        f"- Root: `{project_root}`",
        f"- Overall: `{overall}`",
        "",
        "## Checklist",
    ]
    lines.extend(f"- {item}" for item in checklist)
    if action_sequence:
        lines.extend(["", "## Action Sequence"])
        lines.extend(f"{index}. {item}" for index, item in enumerate(action_sequence, start=1))
    if runbook_steps:
        lines.extend(["", "## Onboarding Runbook"])
        for index, step in enumerate(runbook_steps, start=1):
            lines.extend(
                [
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
                ]
            )
    lines.extend(["## Group Health"])
    for group_name, group_checks in grouped_checks:
        lines.append(f"### {group_name}")
        lines.append(f"- Summary: {_doctor_group_summary(group_name, group_checks)}")
        for status, key, detail in group_checks:
            lines.append(f"- [{status}] `{key}` {detail}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _doctor_refactor_watch_markdown(
    project_id: str,
    project_root: Path,
    grouped_checks: list[tuple[str, list[tuple[str, str, str]]]],
) -> str:
    refactor_findings = [
        (status, detail)
        for _group_name, group_checks in grouped_checks
        for status, key, detail in group_checks
        if key == "refactor_watch"
    ]
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
            lines.append(
                f"{index}. [{hotspot.status}] `{hotspot.identifier}` line={hotspot.line} "
                f"metrics=(lines={hotspot.effective_lines}, branches={hotspot.branches}, nesting={hotspot.nesting}, locals={hotspot.local_vars})"
            )
            lines.append(f"   - token: `{hotspot.rank_token}`")
            lines.append(f"   - issues: `{', '.join(hotspot.issues)}`")
            lines.append(f"   - bundle command: `{command}`")
        extra_findings = refactor_findings[len(hotspots):]
        for index, (status, detail) in enumerate(extra_findings, start=len(hotspots) + 1):
            lines.append(f"{index}. [{status}] {detail}")
    lines.extend(
        [
            "",
            "## Suggested Action",
            "",
            "1. Run `amem refactor-bundle .` to materialize the first hotspot into an executable planning bundle.",
            "2. If a hotspot cannot be split yet, add a guiding comment that explains the main decision path and risk boundaries.",
            "3. Re-run `amem doctor .` after the change and confirm `refactor_watch` findings shrink or disappear.",
        ]
    )
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
    if not isinstance(data, dict):
        return None
    return data


def _state_steps(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _state_pending_steps(state: dict[str, object]) -> list[dict[str, object]]:
    return _state_steps(state.get("runbook_steps"))


def _state_recommended_steps(state: dict[str, object]) -> list[dict[str, object]]:
    return _state_steps(state.get("recommended_steps"))

def _recommended_step_metadata(step: dict[str, object]) -> dict[str, object]:
    return {
        "recommended_next_group": step.get("group"),
        "recommended_next_key": step.get("key"),
        "recommended_next_command": step.get("command"),
        "recommended_verify_command": step.get("verify_with") or "amem doctor .",
        "recommended_done_when": step.get("done_when") or "No pending onboarding steps remain.",
        "recommended_next_safe_to_auto_execute": bool(step.get("safe_to_auto_execute")),
        "recommended_next_approval_required": bool(step.get("approval_required")),
        "recommended_next_approval_reason": step.get("approval_reason"),
    }

def _reconcile_recommended_refactor_state(existing_state: dict[str, object] | None, project_root: Path) -> tuple[list[dict[str, object]], dict[str, object] | None]:
    if existing_state is None:
        return [], None

    hotspots = collect_refactor_watch_hotspots(project_root)
    active_identifiers = {hotspot.identifier for hotspot in hotspots}
    active_tokens = {hotspot.rank_token for hotspot in hotspots}
    if not active_identifiers:
        preserved_steps = [step for step in _state_recommended_steps(existing_state) if step.get("key") != "refactor_bundle"]
        return preserved_steps, None

    preserved_steps: list[dict[str, object]] = []
    for step in _state_recommended_steps(existing_state):
        if step.get("key") != "refactor_bundle":
            preserved_steps.append(step)
            continue
        hotspot = step.get("hotspot")
        identifier = hotspot.get("identifier") if isinstance(hotspot, dict) else None
        token = hotspot.get("rank_token") if isinstance(hotspot, dict) else None
        if token in active_tokens or identifier in active_identifiers:
            preserved_steps.append(step)

    bundle = existing_state.get("recommended_refactor_bundle")
    preserved_bundle: dict[str, object] | None = None
    if isinstance(bundle, dict):
        hotspot = bundle.get("hotspot")
        identifier = hotspot.get("identifier") if isinstance(hotspot, dict) else None
        token = hotspot.get("rank_token") if isinstance(hotspot, dict) else None
        if token in active_tokens or identifier in active_identifiers:
            preserved_bundle = bundle
    return preserved_steps, preserved_bundle


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

    if bridge_rel:
        agents_ref_exists = project_agents_reference_exists(project_root, bridge_rel)
        checks.append((("INFO" if agents_ref_exists else "WARN"), "agents_read_order", "bridge referenced in AGENTS/docs/AGENTS" if agents_ref_exists else "bridge not referenced in AGENTS.md or docs/AGENTS.md (optional but recommended)"))
    else:
        checks.append(("INFO", "agents_read_order", "bridge not configured; AGENTS read order check skipped"))
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
            "recommended_command": "python3 scripts/memory.py doctor . --write-state --write-checklist",
        }

    runbook_steps = state.get("runbook_steps") or []
    recommended_steps = state.get("recommended_steps") or []
    if runbook_steps and not isinstance(runbook_steps, list):
        return {
            "status": "invalid",
            "project_root": str(project_root),
            "message": "Onboarding state is present but malformed.",
            "recommended_command": "python3 scripts/memory.py doctor . --write-state --write-checklist",
        }
    if recommended_steps and not isinstance(recommended_steps, list):
        return {
            "status": "invalid",
            "project_root": str(project_root),
            "message": "Onboarding state is present but malformed.",
            "recommended_command": "python3 scripts/memory.py doctor . --write-state --write-checklist",
        }
    first_step = _runbook_step_from_state(state)
    if (isinstance(runbook_steps, list) and runbook_steps and first_step is None) or (isinstance(recommended_steps, list) and recommended_steps and first_step is None):
        return {
            "status": "invalid",
            "project_root": str(project_root),
            "message": "Onboarding state is present but malformed.",
            "recommended_command": "python3 scripts/memory.py doctor . --write-state --write-checklist",
        }
    if first_step is None:
        return {
            "status": "ready",
            "project_root": str(project_root),
            "project_bootstrap_ready": bool(state.get("project_bootstrap_ready")),
            "project_bootstrap_complete": bool(state.get("project_bootstrap_complete")),
            "message": "No pending onboarding action. Continue with normal implementation flow.",
            "recommended_command": None,
            "verify_with": state.get("recommended_verify_command") or "amem doctor .",
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
                Path(report["project_root"]),
                str(report["overall"]),
                list(report["grouped_checks"]),
                list(report["action_sequence"]),
                list(report["runbook_steps"]),
                list(report["checklist"]),
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
        checklist_path.write_text(
            _doctor_checklist_markdown(project_id, project_root, overall, grouped_checks, action_sequence, runbook_steps, checklist),
            encoding="utf-8",
        )
        log_file_update(ctx.logger, action="write_doctor_checklist", path=checklist_path, detail=f"project_id={project_id};overall={overall}")
        written.append(checklist_path)
        refactor_watch_path = project_root / "docs" / "plans" / "refactor-watch.md"
        refactor_watch_path.parent.mkdir(parents=True, exist_ok=True)
        refactor_watch_path.write_text(
            _doctor_refactor_watch_markdown(project_id, project_root, grouped_checks),
            encoding="utf-8",
        )
        log_file_update(ctx.logger, action="write_refactor_watch", path=refactor_watch_path, detail=f"project_id={project_id};overall={overall}")
        written.append(refactor_watch_path)
    if write_state:
        state_path = project_root / ".agents-memory" / "onboarding-state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps(
                _doctor_state_payload(project_id, project_root, overall, grouped_checks, action_sequence, runbook_steps, checklist, existing_state=existing_state),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        log_file_update(ctx.logger, action="write_doctor_state", path=state_path, detail=f"project_id={project_id};overall={overall}")
        written.append(state_path)
    return written


def cmd_doctor(
    ctx: AppContext,
    project_id_or_path: str = ".",
    write_state: bool = False,
    write_checklist: bool = False,
) -> None:
    # Doctor is the human-readable control panel for the computed report: keep
    # rendering here, but derive the actual project state from `_doctor_report`.
    report = _doctor_report(ctx, project_id_or_path)
    if report is None:
        ctx.logger.warning("doctor_failed | target=%s | reason=unknown_project_or_path", project_id_or_path)
        print(f"项目 '{project_id_or_path}' 未注册，且不是有效目录。")
        print(REGISTER_HINT)
        return
    project_id = str(report["project_id"])
    project_root = Path(report["project_root"])
    overall = str(report["overall"])
    grouped_checks = list(report["grouped_checks"])

    print("\n=== Agents-Memory Doctor ===")
    print(f"Project: {project_id}")
    print(f"Root:    {project_root}")
    print(f"Overall: {overall}\n")
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

    action_sequence = list(report["action_sequence"])
    if action_sequence:
        print("Action Sequence:")
        for index, action in enumerate(action_sequence, start=1):
            print(f"{index}. {action}")
        print()

    runbook_steps = list(report["runbook_steps"])
    if runbook_steps:
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

    checklist = list(report["checklist"])
    if checklist:
        print("Project Bootstrap Checklist:")
        for item in checklist:
            print(f"- {item}")
        print()

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
    if written_artifacts:
        print("Exported Artifacts:")
        for path in written_artifacts:
            print(f"- {path}")
        print()

    print("\nNext:")
    if overall == "READY":
        print("1. 在该项目的 VS Code Agent/Chat 面板中调用 memory_get_index 进行最终运行时验证")
        print(f"2. 如需观察后续接入动作日志，执行: tail -f {ctx.base_dir / 'logs' / 'agents-memory.log'}")
    else:
        print("1. 先修复上面的 FAIL / WARN 项")
        print(f"2. 修复后重新运行: amem doctor {project_id}")
    ctx.logger.info("doctor_complete | project_id=%s | project_root=%s | overall=%s", project_id, project_root, overall)


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
        print("\n=== Onboarding Execute ===")
        print(f"Project Root: {project_root}")
        print(f"Status:       {status}")
        print(f"Message:      {result.get('message')}")
        approval_reason = result.get("approval_reason")
        if approval_reason:
            print(f"Approval:     {approval_reason}")
        recommended_command = result.get("recommended_command")
        if recommended_command:
            print(f"Next:         {recommended_command}")
        return

    step = result.get("step") or {}
    execution = result.get("execution") or {}
    verify_result = result.get("verify") or {}

    print("\n=== Onboarding Execute ===")
    print(f"Project Root: {project_root}")
    print(f"Step:         {step.get('group')} / {step.get('key')}")
    print(f"Status:       {status}")
    print(f"Command:      {execution.get('command')}")
    print(f"Resolved:     {execution.get('resolved_command')}")
    print(f"Return Code:  {execution.get('returncode')}")
    if execution.get("stdout"):
        print("\nExecution stdout:")
        print(execution["stdout"])
    if execution.get("stderr"):
        print("\nExecution stderr:")
        print(execution["stderr"])

    if verify_result:
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

    print("\nState:")
    print(f"- Updated: {result.get('state_updated')}")
    print(f"- Artifacts refreshed: {result.get('artifacts_refreshed')}")
    print(f"- Approval used: {result.get('approval_used')}")
    for path in result.get("written_artifacts", []):
        print(f"- {path}")

    next_action = result.get("next_action") or {}
    if isinstance(next_action, dict):
        print("\nNext Action:")
        print(f"- Status: {next_action.get('status')}")
        if next_action.get("command"):
            print(f"- Command: {next_action.get('command')}")
        elif next_action.get("recommended_command"):
            print(f"- Command: {next_action.get('recommended_command')}")


def offer_agent_setup(ctx: AppContext, project_root: Path, project_id: str, agent_name: str = DEFAULT_AGENT) -> None:
    adapter = get_agent_adapter(agent_name)
    if adapter is None:
        print(f"\n⚠️  未找到 agent adapter: {agent_name}，跳过安装。")
        return
    prompt = f"\n自动安装 {adapter.display_name} 仓库级激活？[Y/n]: " if agent_name != DEFAULT_AGENT else "\n自动安装 .github/copilot-instructions.md（仓库级 Copilot 自动激活）？[Y/n]: "
    answer = input(prompt).strip().lower()
    if answer in ("", "y", "yes"):
        ctx.logger.info("agent_setup_accept | agent=%s | project_id=%s | root=%s", agent_name, project_id, project_root)
        install_agent_adapter(ctx, agent_name, project_root, project_id)
    else:
        ctx.logger.info("agent_setup_skip | agent=%s | project_id=%s | reason=user_declined", agent_name, project_id)
        print(f"跳过。稍后可手动运行: amem agent-setup {agent_name} {project_id}")


def offer_bridge_install(ctx: AppContext, project_id: str) -> None:
    template_path = ctx.templates_dir / BRIDGE_TEMPLATE_NAME
    if not template_path.exists():
        ctx.logger.warning("bridge_offer_skip | project_id=%s | reason=template_missing | template=%s", project_id, template_path)
        print(f"\n⚠️  Bridge 模板不存在: {template_path}，跳过安装。")
        return
    answer = input("\n自动安装 bridge instruction？[Y/n]: ").strip().lower()
    if answer in ("", "y", "yes"):
        ctx.logger.info("bridge_install_accept | project_id=%s", project_id)
        cmd_bridge_install(ctx, project_id)
    else:
        ctx.logger.info("bridge_install_skip | project_id=%s | reason=user_declined", project_id)
        print(f"跳过。稍后可手动运行: python3 scripts/memory.py bridge-install {project_id}")


def offer_mcp_setup(ctx: AppContext, project_id: str, project_root: Path) -> None:
    mcp_file = project_root / VSCODE_DIRNAME / MCP_CONFIG_NAME
    already_has = False
    if mcp_file.exists():
        try:
            already_has = "agents-memory" in json.loads(mcp_file.read_text(encoding="utf-8")).get("servers", {})
        except Exception:
            pass
    if already_has:
        ctx.logger.info("mcp_setup_skip | project_id=%s | reason=already_present | path=%s", project_id, mcp_file)
        print("\nℹ️  .vscode/mcp.json 已包含 agents-memory 配置，跳过。")
        return
    answer = input("\n自动写入 .vscode/mcp.json（VS Code MCP 工具层）？[Y/n]: ").strip().lower()
    if answer in ("", "y", "yes"):
        ctx.logger.info("mcp_setup_accept | project_id=%s | root=%s", project_id, project_root)
        write_vscode_mcp_json(ctx, project_root)
    else:
        ctx.logger.info("mcp_setup_skip | project_id=%s | reason=user_declined", project_id)
        print(f"跳过。稍后可手动运行: amem mcp-setup {project_id}")


def cmd_register(ctx: AppContext, path: str = ".") -> None:
    # Registration is intentionally interactive because it binds together
    # project identity, detected domains, managed instruction roots, and the
    # follow-up integration steps that should run immediately afterward.
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        ctx.logger.warning("register_skip | path=%s | reason=path_not_found", root)
        print(f"路径不存在: {root}")
        return
    ctx.logger.info("register_start | root=%s", root)

    detected_id = detect_project_id(root)
    print(f"\n🔍 检测到项目 ID: {detected_id}  (来源: git remote / 目录名)")
    project_id = (input(f"Project ID [{detected_id}]: ").strip() or detected_id).lower().replace("_", "-")
    if project_already_registered(ctx, project_id):
        ctx.logger.info("register_skip | project_id=%s | reason=already_registered", project_id)
        print(f"⚠️  '{project_id}' 已在 memory/projects.md 中注册，跳过写入。")
        print("如需更新，请手动编辑 memory/projects.md。")
        offer_agent_setup(ctx, root, project_id)
        offer_bridge_install(ctx, project_id)
        offer_mcp_setup(ctx, project_id, root)
        return

    default_instruction_dir = ".github/instructions"
    instruction_dir_input = input(f"Instruction 目录 [{default_instruction_dir}]: ").strip() or default_instruction_dir
    instruction_dir = root / instruction_dir_input
    domains = detect_domains(instruction_dir)
    instruction_files = detect_instruction_files(instruction_dir, root)

    print("\n📂 扫描到 instruction 文件:")
    if instruction_files:
        for domain, instruction_path in instruction_files.items():
            print(f"   {domain:<12} → {instruction_path}")
    else:
        print("   (未找到 .instructions.md 文件，将使用空映射)")
    print(f"\n🏷  推断的 domains: {', '.join(domains)}")
    domains_input = input(f"Domains (逗号分隔) [{', '.join(domains)}]: ").strip()
    if domains_input:
        domains = [domain.strip() for domain in domains_input.split(",") if domain.strip()]

    bridge_rel = f"{instruction_dir_input}/{Path(DEFAULT_BRIDGE_INSTRUCTION_REL).name}"
    instruction_lines = ""
    if instruction_files:
        instruction_lines = "- **instruction_files**:\n"
        for domain, instruction_path in instruction_files.items():
            instruction_lines += f"  - {domain:<12}: {instruction_path}\n"

    entry = (
        f"## {project_id}\n\n"
        f"- **id**: {project_id}\n"
        f"- **root**: {root}\n"
        f"- **instruction_dir**: {instruction_dir_input}\n"
        f"- **bridge_instruction**: {bridge_rel}\n"
        f"- **active**: true\n"
        f"- **domains**: {', '.join(domains)}\n"
        f"{instruction_lines}"
        f"\n---\n"
    )
    append_project_entry(ctx, entry)
    ctx.logger.info("register_complete | project_id=%s | root=%s | domains=%s", project_id, root, ",".join(domains))
    print(f"\n✅ 已写入 memory/projects.md → {project_id}")

    offer_agent_setup(ctx, root, project_id)
    offer_bridge_install(ctx, project_id)
    offer_mcp_setup(ctx, project_id, root)


def _render_project_registry_entry(project_id: str, root: Path, instruction_dir_input: str) -> str:
    instruction_dir = root / instruction_dir_input
    domains = detect_domains(instruction_dir)
    instruction_files = detect_instruction_files(instruction_dir, root)
    bridge_rel = f"{instruction_dir_input}/{Path(DEFAULT_BRIDGE_INSTRUCTION_REL).name}"
    instruction_lines = ""
    if instruction_files:
        instruction_lines = "- **instruction_files**:\n"
        for domain, instruction_path in instruction_files.items():
            instruction_lines += f"  - {domain:<12}: {instruction_path}\n"
    return (
        f"## {project_id}\n\n"
        f"- **id**: {project_id}\n"
        f"- **root**: {root}\n"
        f"- **instruction_dir**: {instruction_dir_input}\n"
        f"- **bridge_instruction**: {bridge_rel}\n"
        f"- **active**: true\n"
        f"- **domains**: {', '.join(domains)}\n"
        f"{instruction_lines}"
        f"\n---\n"
    )


def _ensure_registered_project(ctx: AppContext, project_root: Path) -> tuple[str, bool]:
    project_id, resolved_root, _project = resolve_project_target(ctx, str(project_root))
    root = resolved_root or project_root
    if project_already_registered(ctx, project_id):
        return project_id, False
    append_project_entry(ctx, _render_project_registry_entry(project_id, root, ".github/instructions"))
    ctx.logger.info("enable_register_complete | project_id=%s | root=%s", project_id, root)
    return project_id, True


def _doctor_artifact_paths(project_root: Path, *, write_state: bool, write_checklist: bool) -> list[Path]:
    artifacts: list[Path] = []
    if write_checklist:
        artifacts.append(project_root / "docs" / "plans" / "bootstrap-checklist.md")
        artifacts.append(project_root / "docs" / "plans" / "refactor-watch.md")
    if write_state:
        artifacts.append(project_root / ".agents-memory" / "onboarding-state.json")
    return artifacts


def _preview_enable_profile_actions(ctx: AppContext, project_root: Path, *, full: bool) -> tuple[list[str], list[str], list[str]]:
    capabilities: list[str] = []
    planned_writes: list[str] = []
    skipped_existing: list[str] = []

    applied_profile_id = detect_applied_profile(project_root)
    if full and not applied_profile_id:
        recommended_profile_id = _recommended_enable_profile_id(project_root)
        if not recommended_profile_id:
            skipped_existing.append("profile auto-apply skipped: no default profile detected")
            return capabilities, planned_writes, skipped_existing

        capabilities.append(f"apply recommended profile `{recommended_profile_id}`")
        profile = load_profile(ctx, recommended_profile_id)
        expected = expected_profile_paths(profile, project_root)
        planned_writes.extend(str(path) for path in expected["bootstrap_dirs"])
        planned_writes.extend(str(path) for path in expected["standard_files"])
        planned_writes.extend(str(path) for path in expected["template_files"])
        planned_writes.append(str(project_root / PROFILE_MANIFEST_REL))
        return capabilities, planned_writes, skipped_existing

    if applied_profile_id:
        skipped_existing.append(f"profile already applied: `{applied_profile_id}`")
    else:
        skipped_existing.append("profile auto-apply skipped in default mode")
    return capabilities, planned_writes, skipped_existing


def _preview_onboarding_bundle_actions(ctx: AppContext, project_root: Path) -> tuple[list[str], list[str]]:
    report = _doctor_report(ctx, str(project_root))
    recommended_key = "onboarding"
    if isinstance(report, dict):
        runbook_steps = report.get("runbook_steps")
        if isinstance(runbook_steps, list) and runbook_steps and isinstance(runbook_steps[0], dict):
            recommended_key = str(runbook_steps[0].get("key") or recommended_key)

    onboarding_slug = f"onboarding-{recommended_key.replace('_', '-')}"
    onboarding_plan_root = project_root / "docs" / "plans" / onboarding_slug
    planned_writes = [
        str(onboarding_plan_root / filename)
        for filename in ("README.md", "spec.md", "plan.md", "task-graph.md", "validation.md")
    ]
    return ["generate onboarding planning bundle"], planned_writes


def _preview_refactor_bundle_actions(project_root: Path) -> tuple[list[str], list[str], list[str]]:
    hotspots = collect_refactor_watch_hotspots(project_root)
    if not hotspots:
        return [], [], ["refactor bundle generation skipped: no hotspots"]

    hotspot = hotspots[0]
    refactor_slug = f"refactor-{re.sub(r'[^a-zA-Z0-9]+', '-', f'{hotspot.relative_path}-{hotspot.function_name}'.lower()).strip('-') or 'untitled-task'}"
    refactor_root = project_root / "docs" / "plans" / refactor_slug
    planned_writes = [
        str(refactor_root / filename)
        for filename in ("README.md", "spec.md", "plan.md", "task-graph.md", "validation.md")
    ]
    planned_writes.append(str(project_root / ".agents-memory" / "onboarding-state.json"))
    capability = f"generate refactor bundle for `{hotspot.identifier}` using `{hotspot.rank_token}`"
    return [capability], planned_writes, []


def _preview_enable_actions(ctx: AppContext, project_root: Path, *, project_id: str, full: bool) -> dict[str, object]:
    capabilities: list[str] = []
    planned_writes: list[str] = []
    skipped_existing: list[str] = []

    if not project_already_registered(ctx, project_id):
        capabilities.append(f"register project `{project_id}`")
        planned_writes.append(str(ctx.projects_file))
    else:
        skipped_existing.append(f"registry entry already exists for `{project_id}`")

    bridge_path = project_root / DEFAULT_BRIDGE_INSTRUCTION_REL
    if not bridge_path.exists():
        capabilities.append("install bridge instruction")
        planned_writes.append(str(bridge_path))
    else:
        skipped_existing.append(str(bridge_path))

    mcp_path = project_root / VSCODE_DIRNAME / MCP_CONFIG_NAME
    capabilities.append("merge agents-memory MCP server config")
    planned_writes.append(str(mcp_path))

    profile_capabilities, profile_writes, profile_skipped = _preview_enable_profile_actions(ctx, project_root, full=full)
    capabilities.extend(profile_capabilities)
    planned_writes.extend(profile_writes)
    skipped_existing.extend(profile_skipped)

    if full:
        capabilities.append("install or update Copilot activation block")
        planned_writes.append(str(project_root / COPILOT_INSTRUCTIONS_REL))

    capabilities.append("refresh doctor state and checklist artifacts")
    planned_writes.extend(str(path) for path in _doctor_artifact_paths(project_root, write_state=True, write_checklist=True))

    onboarding_capabilities, onboarding_writes = _preview_onboarding_bundle_actions(ctx, project_root)
    capabilities.extend(onboarding_capabilities)
    planned_writes.extend(onboarding_writes)

    if full:
        refactor_capabilities, refactor_writes, refactor_skipped = _preview_refactor_bundle_actions(project_root)
        capabilities.extend(refactor_capabilities)
        planned_writes.extend(refactor_writes)
        skipped_existing.extend(refactor_skipped)

    return {
        "status": "ok",
        "project_id": project_id,
        "project_root": str(project_root),
        "mode": "full" if full else "default",
        "dry_run": True,
        "capabilities": capabilities,
        "planned_writes": list(dict.fromkeys(planned_writes)),
        "skipped_existing": skipped_existing,
    }


def _recommended_enable_profile_id(project_root: Path) -> str | None:
    if detect_applied_profile(project_root):
        return None
    if (project_root / "package.json").exists() and (project_root / "apps").exists():
        return "fullstack-product"
    if (project_root / "package.json").exists() and ((project_root / "src").exists() or (project_root / "app").exists()):
        return "frontend-app"
    if (project_root / "scripts" / "mcp_server.py").exists() or (project_root / "runtime").exists():
        return "agent-runtime"
    if any((project_root / name).exists() for name in ("pyproject.toml", "requirements.txt", "setup.py")):
        return "python-service"
    if list(project_root.glob("**/*.py")):
        return "python-service"
    return None


def _validate_enable_request(project_root: Path, *, dry_run: bool, json_output: bool) -> int | None:
    if not project_root.exists():
        print(f"路径不存在: {project_root}")
        return 1
    if not project_root.is_dir():
        print(f"目标不是目录: {project_root}")
        return 1
    if json_output and not dry_run:
        print("--json 目前仅支持与 --dry-run 一起使用")
        return 1
    return None


def _print_enable_header(project_root: Path, *, full: bool, dry_run: bool) -> None:
    print("\n=== Agents-Memory Enable ===")
    print(f"Target: {project_root}")
    print(f"Mode:   {'full' if full else 'default'}")
    print(f"DryRun: {'yes' if dry_run else 'no'}")


def _preview_strings(preview: dict[str, object], key: str) -> list[str]:
    values = preview.get(key)
    if not isinstance(values, list):
        return []
    return [str(item) for item in values]


def _render_enable_preview(preview: dict[str, object], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        return

    print("\nCapabilities:")
    for item in _preview_strings(preview, "capabilities"):
        print(f"- {item}")
    print("\nPlanned Writes:")
    for path in _preview_strings(preview, "planned_writes"):
        print(f"- {path}")
    print("\nSkipped Existing:")
    skipped_existing = _preview_strings(preview, "skipped_existing")
    if skipped_existing:
        for item in skipped_existing:
            print(f"- {item}")
    else:
        print("- none")
    print("\nNext:")
    print("- Re-run without --dry-run to apply these changes")


def _run_enable_dry_run(
    ctx: AppContext,
    project_root: Path,
    *,
    project_id: str,
    full: bool,
    json_output: bool,
) -> int:
    preview = _preview_enable_actions(ctx, project_root, project_id=project_id, full=full)
    _render_enable_preview(preview, json_output=json_output)
    ctx.logger.info(
        "enable_preview | target=%s | full=%s | planned_writes=%s",
        project_root,
        full,
        len(_preview_strings(preview, "planned_writes")),
    )
    return 0


def _apply_enable_profile(ctx: AppContext, project_root: Path, *, full: bool) -> str | None:
    applied_profile_id = detect_applied_profile(project_root)
    if full and not applied_profile_id:
        recommended_profile_id = _recommended_enable_profile_id(project_root)
        if not recommended_profile_id:
            print("- profile: skipped (no default profile detected)")
            return None

        profile = load_profile(ctx, recommended_profile_id)
        profile_result = apply_profile(ctx, profile, project_root)
        print(f"- profile: enabled ({profile_result.profile_id})")
        return profile_result.profile_id

    if applied_profile_id:
        print(f"- profile: ready ({applied_profile_id})")
        return applied_profile_id

    print("- profile: skipped in default mode")
    return None


def _write_enable_refactor_followup(
    ctx: AppContext,
    project_root: Path,
    *,
    refactor_result: RefactorBundleResult,
) -> None:
    existing_state = load_onboarding_state(project_root)
    hotspot_payload = {
        "identifier": refactor_result.hotspot.identifier,
        "rank_token": refactor_result.hotspot_token,
        "relative_path": refactor_result.hotspot.relative_path,
        "function_name": refactor_result.hotspot.function_name,
        "qualified_name": refactor_result.hotspot.qualified_name,
        "line": refactor_result.hotspot.line,
        "status": refactor_result.hotspot.status,
        "effective_lines": refactor_result.hotspot.effective_lines,
        "branches": refactor_result.hotspot.branches,
        "nesting": refactor_result.hotspot.nesting,
        "local_vars": refactor_result.hotspot.local_vars,
        "has_guiding_comment": refactor_result.hotspot.has_guiding_comment,
        "issues": refactor_result.hotspot.issues,
        "score": refactor_result.hotspot.score,
    }
    updated_state = _merge_refactor_followup_state(
        existing_state,
        project_root=project_root,
        plan_root=refactor_result.plan_root,
        hotspot_index=refactor_result.hotspot_index,
        hotspot_token=refactor_result.hotspot_token,
        hotspot=hotspot_payload,
        task_name=refactor_result.task_name,
        task_slug=refactor_result.task_slug,
    )
    _write_onboarding_state_file(ctx, project_root, updated_state)


def _run_enable_full_followup(ctx: AppContext, project_root: Path) -> None:
    hotspots = collect_refactor_watch_hotspots(project_root)
    if not hotspots:
        print("- refactor bundle: skipped (no hotspots)")
        return

    from agents_memory.services.planning import init_refactor_bundle

    refactor_result = init_refactor_bundle(ctx, project_root, hotspot_token=hotspots[0].rank_token)
    _write_enable_refactor_followup(ctx, project_root, refactor_result=refactor_result)
    print(f"- refactor bundle: {refactor_result.plan_root.relative_to(project_root).as_posix()} ({refactor_result.hotspot_token})")


def _print_enable_next_steps(*, full: bool) -> None:
    print("\nNext:")
    print("- Review onboarding-state.json and docs/plans/bootstrap-checklist.md")
    print("- Run amem doctor . after your next structural change")
    if full:
        print("- If a refactor bundle was generated, review its spec.md before editing code")


def cmd_enable(ctx: AppContext, project_id_or_path: str = ".", *, full: bool = False, dry_run: bool = False, json_output: bool = False) -> int:
    project_root = Path(project_id_or_path).expanduser().resolve()
    ctx.logger.info("enable_start | target=%s | full=%s | dry_run=%s | json_output=%s", project_root, full, dry_run, json_output)
    validation_error = _validate_enable_request(project_root, dry_run=dry_run, json_output=json_output)
    if validation_error is not None:
        return validation_error
    if not json_output:
        _print_enable_header(project_root, full=full, dry_run=dry_run)

    resolved_project_id, _resolved_root, _project = resolve_project_target(ctx, str(project_root))
    if dry_run:
        return _run_enable_dry_run(ctx, project_root, project_id=resolved_project_id, full=full, json_output=json_output)

    project_id, registered_now = _ensure_registered_project(ctx, project_root)
    print(f"- registry: {'created' if registered_now else 'ready'} ({project_id})")

    project_id, _, _project = resolve_project_target(ctx, project_id)
    cmd_bridge_install(ctx, project_id)
    mcp_changed = write_vscode_mcp_json(ctx, project_root)
    print(f"- mcp config: {'updated' if mcp_changed else 'ready'}")

    _apply_enable_profile(ctx, project_root, full=full)

    if full:
        print("- copilot activation: applying")
        cmd_copilot_setup(ctx, str(project_root))

    cmd_doctor(ctx, str(project_root), write_state=True, write_checklist=True)

    from agents_memory.services.planning import init_onboarding_bundle

    onboarding_result = init_onboarding_bundle(ctx, project_root)
    print(f"- onboarding bundle: {onboarding_result.plan_root.relative_to(project_root).as_posix()}")

    if full:
        _run_enable_full_followup(ctx, project_root)

    _print_enable_next_steps(full=full)
    ctx.logger.info("enable_complete | target=%s | full=%s | dry_run=%s | project_id=%s", project_root, full, dry_run, project_id)
    return 0
