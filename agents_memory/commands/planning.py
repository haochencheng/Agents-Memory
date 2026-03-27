from __future__ import annotations

from agents_memory.services.planning import cmd_onboarding_bundle, cmd_plan_init, cmd_refactor_bundle


def _handle_plan_init(ctx, args: list[str]) -> None:
    # Parse CLI args and dispatch to cmd_plan_init.
    dry_run = False
    task_slug: str | None = None
    positionals: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        index += 1
        if arg == "--dry-run":
            dry_run = True
            continue
        if arg == "--slug" and index < len(args):
            task_slug = args[index]; index += 1
            continue
        positionals.append(arg)

    if not positionals:
        print("用法: python3 memory.py plan-init <task-name> [path] [--slug <task-slug>] [--dry-run]")
        raise SystemExit(1)

    task_name = positionals[0]
    target = positionals[1] if len(positionals) > 1 else "."
    raise SystemExit(cmd_plan_init(ctx, task_name, target, task_slug=task_slug, dry_run=dry_run))


def register() -> dict[str, callable]:
    return {
        "plan-init": _handle_plan_init,
        "onboarding-bundle": _handle_onboarding_bundle,
        "refactor-bundle": _handle_refactor_bundle,
    }


def _handle_onboarding_bundle(ctx, args: list[str]) -> None:
    # Parse CLI args and dispatch to cmd_onboarding_bundle.
    dry_run = False
    task_slug: str | None = None
    positionals: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--dry-run":
            dry_run = True
        elif arg == "--slug" and index + 1 < len(args):
            task_slug = args[index + 1]
            index += 1
        else:
            positionals.append(arg)
        index += 1

    target = positionals[0] if positionals else "."
    raise SystemExit(cmd_onboarding_bundle(ctx, target, task_slug=task_slug, dry_run=dry_run))


def _parse_refactor_bundle_args(args: list[str]) -> tuple:
    # Parse --dry-run, --slug, --token, --index flags from the arg list.
    dry_run = False
    task_slug: str | None = None
    hotspot_index = 1
    hotspot_token: str | None = None
    positionals: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        index += 1
        if arg == "--dry-run":
            dry_run = True
            continue
        if arg == "--slug" and index < len(args):
            task_slug = args[index]; index += 1
            continue
        if arg == "--token" and index < len(args):
            hotspot_token = args[index]; index += 1
            continue
        if arg == "--index" and index < len(args):
            hotspot_index = int(args[index]); index += 1
            continue
        positionals.append(arg)
    return dry_run, task_slug, hotspot_token, hotspot_index, positionals


def _handle_refactor_bundle(ctx, args: list[str]) -> None:
    # Parse CLI args then dispatch to cmd_refactor_bundle.
    dry_run, task_slug, hotspot_token, hotspot_index, positionals = _parse_refactor_bundle_args(args)
    target = positionals[0] if positionals else "."
    raise SystemExit(
        cmd_refactor_bundle(
            ctx,
            target,
            hotspot_index=hotspot_index,
            hotspot_token=hotspot_token,
            task_slug=task_slug,
            dry_run=dry_run,
        )
    )
