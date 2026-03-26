from __future__ import annotations

from collections.abc import Callable

from agents_memory.services.integration import (
    cmd_agent_list,
    cmd_agent_setup,
    cmd_bridge_install,
    cmd_copilot_setup,
    cmd_doctor,
    cmd_enable,
    cmd_mcp_setup,
    cmd_onboarding_execute,
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


def _parse_onboarding_execute_args(args: list[str]) -> tuple[str, bool, bool]:
    project_id_or_path = "."
    verify = True
    approve_unsafe = False
    for arg in args:
        if arg == "--no-verify":
            verify = False
        elif arg == "--approve-unsafe":
            approve_unsafe = True
        elif arg.startswith("--"):
            print(f"未知参数: {arg}")
        else:
            project_id_or_path = arg
    return project_id_or_path, verify, approve_unsafe


def _run_onboarding_execute(ctx, args: list[str]) -> None:
    project_id_or_path, verify, approve_unsafe = _parse_onboarding_execute_args(args)
    cmd_onboarding_execute(ctx, project_id_or_path, verify=verify, approve_unsafe=approve_unsafe)


def _parse_enable_args(args: list[str]) -> tuple[str, bool]:
    project_id_or_path = "."
    full = False
    for arg in args:
        if arg == "--full":
            full = True
        elif arg.startswith("--"):
            print(f"未知参数: {arg}")
        else:
            project_id_or_path = arg
    return project_id_or_path, full


def _run_enable(ctx, args: list[str]) -> None:
    project_id_or_path, full = _parse_enable_args(args)
    raise SystemExit(cmd_enable(ctx, project_id_or_path, full=full))


def register() -> dict[str, Callable]:
    return {
        "sync": lambda ctx, args: cmd_sync(ctx),
        "bridge-install": lambda ctx, args: cmd_bridge_install(ctx, args[0]) if args else print("用法: python3 memory.py bridge-install <project-id>"),
        "copilot-setup": lambda ctx, args: cmd_copilot_setup(ctx, args[0] if args else "."),
        "agent-list": lambda ctx, args: cmd_agent_list(),
        "agent-setup": lambda ctx, args: cmd_agent_setup(ctx, args[0], args[1] if len(args) > 1 else ".") if args else print("用法: python3 memory.py agent-setup <agent> [project-id|path]"),
        "mcp-setup": lambda ctx, args: cmd_mcp_setup(ctx, args[0] if args else "."),
        "doctor": lambda ctx, args: cmd_doctor(ctx, *_parse_doctor_args(args)),
        "onboarding-execute": _run_onboarding_execute,
        "enable": _run_enable,
        "register": lambda ctx, args: cmd_register(ctx, args[0] if args else "."),
    }
