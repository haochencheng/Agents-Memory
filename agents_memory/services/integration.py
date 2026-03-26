from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from agents_memory.constants import (
    BRIDGE_TEMPLATE_NAME,
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
from agents_memory.services.profiles import detect_applied_profile
from agents_memory.services.records import collect_errors
from agents_memory.services.validation import collect_plan_check_findings, collect_profile_check_findings


DOCTOR_GROUP_ORDER = ["Core", "Planning", "Integration", "Optional"]
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


def _doctor_overall(checks: list[tuple[str, str, str]]) -> str:
    required_statuses = [status for status, key, _ in checks if key not in {"agents_read_order", "copilot_activation", "profile_manifest"} and status != "INFO"]
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


def cmd_doctor(ctx: AppContext, project_id_or_path: str = ".") -> None:
    project_id, project_root, project = resolve_project_target(ctx, project_id_or_path)
    ctx.logger.info("doctor_start | target=%s | resolved_project_id=%s | project_root=%s", project_id_or_path, project_id, project_root)
    if project_root is None:
        ctx.logger.warning("doctor_failed | target=%s | reason=unknown_project_or_path", project_id_or_path)
        print(f"项目 '{project_id_or_path}' 未注册，且不是有效目录。")
        print(REGISTER_HINT)
        return

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

    overall = _doctor_overall(checks)

    print("\n=== Agents-Memory Doctor ===")
    print(f"Project: {project_id}")
    print(f"Root:    {project_root}")
    print(f"Overall: {overall}\n")
    for group_name, group_checks in _doctor_group_checks(checks):
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

    print("\nNext:")
    if overall == "READY":
        print("1. 在该项目的 VS Code Agent/Chat 面板中调用 memory_get_index 进行最终运行时验证")
        print(f"2. 如需观察后续接入动作日志，执行: tail -f {ctx.base_dir / 'logs' / 'agents-memory.log'}")
    else:
        print("1. 先修复上面的 FAIL / WARN 项")
        print(f"2. 修复后重新运行: amem doctor {project_id}")
    ctx.logger.info("doctor_complete | project_id=%s | project_root=%s | overall=%s", project_id, project_root, overall)


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
