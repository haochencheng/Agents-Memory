from __future__ import annotations

from agents_memory.services.integration import (
    cmd_agent_list,
    cmd_agent_setup,
    cmd_bridge_install,
    cmd_copilot_setup,
    cmd_doctor,
    cmd_mcp_setup,
    cmd_register,
    cmd_sync,
)


def register() -> dict[str, callable]:
    return {
        "sync": lambda ctx, args: cmd_sync(ctx),
        "bridge-install": lambda ctx, args: cmd_bridge_install(ctx, args[0]) if args else print("用法: python3 memory.py bridge-install <project-id>"),
        "copilot-setup": lambda ctx, args: cmd_copilot_setup(ctx, args[0] if args else "."),
        "agent-list": lambda ctx, args: cmd_agent_list(),
        "agent-setup": lambda ctx, args: cmd_agent_setup(ctx, args[0], args[1] if len(args) > 1 else ".") if args else print("用法: python3 memory.py agent-setup <agent> [project-id|path]"),
        "mcp-setup": lambda ctx, args: cmd_mcp_setup(ctx, args[0] if args else "."),
        "doctor": lambda ctx, args: cmd_doctor(ctx, args[0] if args else "."),
        "register": lambda ctx, args: cmd_register(ctx, args[0] if args else "."),
    }
