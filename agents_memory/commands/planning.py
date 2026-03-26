from __future__ import annotations

from agents_memory.services.planning import cmd_onboarding_bundle, cmd_plan_init, cmd_refactor_bundle


def _handle_plan_init(ctx, args: list[str]) -> None:
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


def _handle_refactor_bundle(ctx, args: list[str]) -> None:
    dry_run = False
    task_slug: str | None = None
    hotspot_index = 1
    positionals: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--dry-run":
            dry_run = True
        elif arg == "--slug" and index + 1 < len(args):
            task_slug = args[index + 1]
            index += 1
        elif arg == "--index" and index + 1 < len(args):
            hotspot_index = int(args[index + 1])
            index += 1
        else:
            positionals.append(arg)
        index += 1

    target = positionals[0] if positionals else "."
    raise SystemExit(
        cmd_refactor_bundle(ctx, target, hotspot_index=hotspot_index, task_slug=task_slug, dry_run=dry_run)
    )
