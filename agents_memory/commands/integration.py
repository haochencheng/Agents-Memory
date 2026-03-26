from __future__ import annotations

from collections.abc import Callable

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


def _parse_doctor_args(args: list[str]) -> tuple[str, bool, bool]:
    project_id_or_path = "."
    write_state = False
    write_checklist = False
    for arg in args:
        if arg == "--write-state":
            write_state = True
        elif arg == "--write-checklist":
            write_checklist = True
        elif arg.startswith("--"):
            print(f"未知参数: {arg}")
        else:
            project_id_or_path = arg
    return project_id_or_path, write_state, write_checklist


def register() -> dict[str, Callable]:
    return {
        "sync": lambda ctx, args: cmd_sync(ctx),
        "bridge-install": lambda ctx, args: cmd_bridge_install(ctx, args[0]) if args else print("用法: python3 memory.py bridge-install <project-id>"),
        "copilot-setup": lambda ctx, args: cmd_copilot_setup(ctx, args[0] if args else "."),
        "agent-list": lambda ctx, args: cmd_agent_list(),
        "agent-setup": lambda ctx, args: cmd_agent_setup(ctx, args[0], args[1] if len(args) > 1 else ".") if args else print("用法: python3 memory.py agent-setup <agent> [project-id|path]"),
        "mcp-setup": lambda ctx, args: cmd_mcp_setup(ctx, args[0] if args else "."),
        "doctor": lambda ctx, args: cmd_doctor(ctx, *_parse_doctor_args(args)),
        "register": lambda ctx, args: cmd_register(ctx, args[0] if args else "."),
    }
