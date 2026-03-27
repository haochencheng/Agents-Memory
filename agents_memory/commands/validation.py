from __future__ import annotations

from collections.abc import Callable

from agents_memory.services.validation import cmd_docs_check, cmd_docs_touch, cmd_plan_check, cmd_profile_check


def _parse_validation_flags(args: list[str]) -> tuple[str, bool, str, str | None]:
    target = "."
    strict = False
    output_format = "text"
    profile_id: str | None = None
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--strict":
            strict = True
        elif arg == "--format" and index + 1 < len(args):
            output_format = args[index + 1]
            index += 1
        elif arg == "--profile" and index + 1 < len(args):
            profile_id = args[index + 1]
            index += 1
        elif not arg.startswith("--"):
            target = arg
        index += 1
    return target, strict, output_format, profile_id


def _handle_docs_check(ctx, args: list[str]) -> None:
    target, strict, output_format, _profile_id = _parse_validation_flags(args)
    raise SystemExit(cmd_docs_check(ctx, target, strict=strict, output_format=output_format))


def _handle_profile_check(ctx, args: list[str]) -> None:
    target, strict, output_format, profile_id = _parse_validation_flags(args)
    raise SystemExit(cmd_profile_check(ctx, target, profile_id=profile_id, strict=strict, output_format=output_format))


def _handle_plan_check(ctx, args: list[str]) -> None:
    target, strict, output_format, _profile_id = _parse_validation_flags(args)
    raise SystemExit(cmd_plan_check(ctx, target, strict=strict, output_format=output_format))


def _parse_docs_touch_flags(args: list[str]) -> tuple[str, str | None, bool, str]:
    target = "."
    updated_at: str | None = None
    dry_run = False
    output_format = "text"
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--date" and index + 1 < len(args):
            updated_at = args[index + 1]
            index += 1
        elif arg == "--dry-run":
            dry_run = True
        elif arg == "--format" and index + 1 < len(args):
            output_format = args[index + 1]
            index += 1
        elif not arg.startswith("--"):
            target = arg
        index += 1
    return target, updated_at, dry_run, output_format


def _handle_docs_touch(ctx, args: list[str]) -> None:
    target, updated_at, dry_run, output_format = _parse_docs_touch_flags(args)
    raise SystemExit(cmd_docs_touch(ctx, target, updated_at=updated_at, dry_run=dry_run, output_format=output_format))


def register() -> dict[str, Callable]:
    return {
        "docs-check": _handle_docs_check,
        "docs-touch": _handle_docs_touch,
        "profile-check": _handle_profile_check,
        "plan-check": _handle_plan_check,
    }
