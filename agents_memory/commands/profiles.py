from __future__ import annotations

from agents_memory.services.profiles import cmd_profile_apply, cmd_profile_list, cmd_profile_render, cmd_profile_show, cmd_standards_sync


def _parse_profile_flags(args: list[str]) -> tuple[list[str], str]:
    positionals: list[str] = []
    output_format = "text"
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--format" and index + 1 < len(args):
            output_format = args[index + 1]
            index += 1
        else:
            positionals.append(arg)
        index += 1
    return positionals, output_format


def _handle_profile_list(ctx, args: list[str]) -> None:
    _positionals, output_format = _parse_profile_flags(args)
    raise SystemExit(cmd_profile_list(ctx, output_format=output_format))


def _handle_profile_show(ctx, args: list[str]) -> None:
    positionals, output_format = _parse_profile_flags(args)
    if not positionals:
        print("用法: python3 memory.py profile-show <profile-id> [--format json]")
        raise SystemExit(1)
    raise SystemExit(cmd_profile_show(ctx, positionals[0], output_format=output_format))


def _handle_profile_apply(ctx, args: list[str]) -> None:
    dry_run = False
    positionals: list[str] = []
    for arg in args:
        if arg == "--dry-run":
            dry_run = True
        else:
            positionals.append(arg)
    if not positionals:
        print("用法: python3 memory.py profile-apply <profile-id> [path] [--dry-run]")
        raise SystemExit(1)
    profile_id = positionals[0]
    target = positionals[1] if len(positionals) > 1 else "."
    raise SystemExit(cmd_profile_apply(ctx, profile_id, target, dry_run=dry_run))


def _handle_profile_diff(ctx, args: list[str]) -> None:
    if not args:
        print("用法: python3 memory.py profile-diff <profile-id> [path]")
        raise SystemExit(1)
    profile_id = args[0]
    target = args[1] if len(args) > 1 else "."
    raise SystemExit(cmd_profile_apply(ctx, profile_id, target, dry_run=True))


def _handle_standards_sync(ctx, args: list[str]) -> None:
    # Parse CLI args and dispatch to cmd_standards_sync.
    dry_run = False
    profile_id: str | None = None
    positionals: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--dry-run":
            dry_run = True
        elif arg == "--profile" and index + 1 < len(args):
            profile_id = args[index + 1]
            index += 1
        else:
            positionals.append(arg)
        index += 1

    target = positionals[0] if positionals else "."
    raise SystemExit(cmd_standards_sync(ctx, target, profile_id=profile_id, dry_run=dry_run))


def _handle_profile_render(ctx, args: list[str]) -> None:
    dry_run = False
    profile_id: str | None = None
    positionals: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--dry-run":
            dry_run = True
        elif arg == "--profile" and index + 1 < len(args):
            profile_id = args[index + 1]
            index += 1
        else:
            positionals.append(arg)
        index += 1

    target = positionals[0] if positionals else "."
    raise SystemExit(cmd_profile_render(ctx, target, profile_id=profile_id, dry_run=dry_run))


def register() -> dict[str, callable]:
    return {
        "profile-list": _handle_profile_list,
        "profile-show": _handle_profile_show,
        "profile-apply": _handle_profile_apply,
        "profile-diff": _handle_profile_diff,
        "profile-render": _handle_profile_render,
        "standards-sync": _handle_standards_sync,
    }
