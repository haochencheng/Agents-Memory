from __future__ import annotations

from collections.abc import Callable

from agents_memory.services.validation import cmd_docs_check, cmd_docs_touch, cmd_plan_check, cmd_profile_check


def _parse_validation_flags(args: list[str]) -> tuple[str, bool, str, str | None]:
    # Parse --strict, --format, --profile flags; first positional is target.
    target = "."
    strict = False
    output_format = "text"
    profile_id: str | None = None
    index = 0
    while index < len(args):
        arg = args[index]
        index += 1
        if arg == "--strict":
            strict = True; continue
        if arg == "--format" and index < len(args):
            output_format = args[index]; index += 1; continue
        if arg == "--profile" and index < len(args):
            profile_id = args[index]; index += 1; continue
        if not arg.startswith("--"):
            target = arg
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
    # Parse --date, --dry-run, --format flags; first positional is target.
    target = "."
    updated_at: str | None = None
    dry_run = False
    output_format = "text"
    index = 0
    while index < len(args):
        arg = args[index]
        index += 1
        if arg == "--date" and index < len(args):
            updated_at = args[index]; index += 1; continue
        if arg == "--dry-run":
            dry_run = True; continue
        if arg == "--format" and index < len(args):
            output_format = args[index]; index += 1; continue
        if not arg.startswith("--"):
            target = arg
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
