from __future__ import annotations

import json
from pathlib import Path

from agents_memory.constants import BRIDGE_TEMPLATE_NAME, DEFAULT_BRIDGE_INSTRUCTION_REL, MCP_CONFIG_NAME, VSCODE_DIRNAME
from agents_memory.integrations.agents.registry import DEFAULT_AGENT, get_agent_adapter
from agents_memory.runtime import AppContext
from agents_memory.services.integration_setup import cmd_bridge_install, install_agent_adapter, write_vscode_mcp_json
from agents_memory.services.projects import (
    append_project_entry,
    detect_domains,
    detect_instruction_files,
    detect_project_id,
    project_already_registered,
    resolve_project_target,
)


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

    entry = _render_project_registry_entry(project_id, root, instruction_dir_input)
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