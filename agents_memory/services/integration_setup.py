from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from agents_memory.constants import BRIDGE_TEMPLATE_NAME, MCP_CONFIG_NAME, PYTHON_BIN, REGISTER_HINT, VSCODE_DIRNAME
from agents_memory.integrations.agents.registry import DEFAULT_AGENT, get_agent_adapter, list_agent_adapters
from agents_memory.logging_utils import log_file_update
from agents_memory.runtime import AppContext
from agents_memory.services.projects import parse_projects, resolve_bridge_rel, resolve_project_target
from agents_memory.services.records import collect_errors


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


def _sync_target_path(projects: list[dict], rel_path: str) -> Path | None:
    for project in projects:
        root = project.get("root", "").strip()
        if not root:
            continue
        candidate = Path(root) / rel_path
        if candidate.exists():
            return candidate
    return None


def _append_gotcha_entry(target_content: str, record_id: str, rule_text: str) -> str:
    gotcha_entry = f"\n- **[`{record_id}`]** {rule_text}\n  <!-- auto-synced from agents-memory -->"
    if "## ⚠️ Gotchas" in target_content:
        return target_content.replace("## ⚠️ Gotchas", f"## ⚠️ Gotchas\n{gotcha_entry}", 1)
    return target_content + f"\n\n## ⚠️ Gotchas\n{gotcha_entry}\n"


def _sync_record(ctx: AppContext, projects: list[dict], record: dict) -> bool:
    raw_path = record.get("promoted_to", "").strip('"').strip("'")
    if not raw_path:
        return False

    rel_path = re.sub(r"\s*\(.*\)\s*$", "", raw_path).strip()
    abs_target = _sync_target_path(projects, rel_path)
    record_id = record.get("id", "unknown")
    if abs_target is None:
        ctx.logger.warning("sync_target_missing | record_id=%s | target=%s", record_id, rel_path)
        print(f"  ⚠  [{record_id}] target not found: {rel_path}")
        return False

    target_content = abs_target.read_text(encoding="utf-8")
    if record_id in target_content:
        ctx.logger.info("sync_skip | record_id=%s | reason=already_synced | target=%s", record_id, abs_target)
        print(f"  ✓  [{record_id}] already synced → {abs_target.name}")
        return False

    rule_text = extract_rule_text(Path(record["_file"]))
    if not rule_text:
        ctx.logger.warning("sync_skip | record_id=%s | reason=no_rule_text", record_id)
        print(f"  ⚠  [{record_id}] no rule text found, skipping")
        return False

    abs_target.write_text(_append_gotcha_entry(target_content, record_id, rule_text), encoding="utf-8")
    log_file_update(ctx.logger, action="sync_rule", path=abs_target, detail=f"record_id={record_id}")
    print(f"  ✅ [{record_id}] synced → {abs_target}")
    return True


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
        if _sync_record(ctx, projects, record):
            synced += 1
        else:
            skipped += 1

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