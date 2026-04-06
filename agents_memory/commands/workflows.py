from __future__ import annotations

from collections.abc import Callable

from agents_memory.services.workflows import cmd_bootstrap, cmd_close_task, cmd_do_next, cmd_start_task, cmd_validate


def _parse_bootstrap_args(args: list[str]) -> tuple[str, bool, bool, bool]:
    # Parse --full, --dry-run, --json flags; first positional is target.
    project_id_or_path = "."
    full = False
    dry_run = False
    json_output = False
    for arg in args:
        if arg == "--full":
            full = True
            continue
        if arg == "--dry-run":
            dry_run = True
            continue
        if arg == "--json":
            json_output = True
            continue
        if arg.startswith("--"):
            print(f"未知参数: {arg}")
            continue
        project_id_or_path = arg
    return project_id_or_path, full, dry_run, json_output


def _handle_bootstrap(ctx, args: list[str]) -> None:
    project_id_or_path, full, dry_run, json_output = _parse_bootstrap_args(args)
    raise SystemExit(cmd_bootstrap(ctx, project_id_or_path, full=full, dry_run=dry_run, json_output=json_output))


def _handle_start_task(ctx, args: list[str]) -> None:
    # Parse CLI args and dispatch to cmd_start_task.
    dry_run = False
    wiki_context = False
    task_slug: str | None = None
    positionals: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        index += 1
        if arg == "--dry-run":
            dry_run = True
            continue
        if arg == "--wiki-context":
            wiki_context = True
            continue
        if arg == "--slug" and index < len(args):
            task_slug = args[index]; index += 1
            continue
        positionals.append(arg)

    if not positionals:
        print('用法: python3 memory.py start-task <task-name> [path] [--slug <task-slug>] [--wiki-context] [--dry-run]')
        raise SystemExit(1)

    task_name = positionals[0]
    target = positionals[1] if len(positionals) > 1 else "."
    raise SystemExit(cmd_start_task(ctx, task_name, target, task_slug=task_slug, dry_run=dry_run, wiki_context=wiki_context))


def _parse_format_args(args: list[str]) -> tuple[str, str, bool]:
    # Parse --format, --strict flags; first positional is target.
    target = "."
    output_format = "text"
    strict = False
    index = 0
    while index < len(args):
        arg = args[index]
        index += 1
        if arg == "--format" and index < len(args):
            output_format = args[index]; index += 1; continue
        if arg == "--strict":
            strict = True; continue
        if arg.startswith("--"):
            print(f"未知参数: {arg}"); continue
        target = arg
    return target, output_format, strict


def _handle_do_next(ctx, args: list[str]) -> None:
    target, output_format, _strict = _parse_format_args(args)
    raise SystemExit(cmd_do_next(ctx, target, output_format=output_format))


def _handle_validate(ctx, args: list[str]) -> None:
    target, output_format, strict = _parse_format_args(args)
    raise SystemExit(cmd_validate(ctx, target, strict=strict, output_format=output_format))


def _handle_close_task(ctx, args: list[str]) -> None:
    # Parse CLI args and dispatch to cmd_close_task.
    target = "."
    task_slug: str | None = None
    output_format = "text"
    bool_flags: set[str] = set()
    index = 0
    while index < len(args):
        arg = args[index]
        index += 1
        if arg == "--slug" and index < len(args):
            task_slug = args[index]; index += 1; continue
        if arg == "--format" and index < len(args):
            output_format = args[index]; index += 1; continue
        if arg in {"--strict", "--skip-global-gate"}:
            bool_flags.add(arg); continue
        if arg.startswith("--"):
            print(f"未知参数: {arg}"); continue
        target = arg
    raise SystemExit(cmd_close_task(
        ctx,
        target,
        task_slug=task_slug,
        strict="--strict" in bool_flags,
        output_format=output_format,
        skip_global_gate="--skip-global-gate" in bool_flags,
    ))


def register() -> dict[str, Callable]:
    return {
        "bootstrap": _handle_bootstrap,
        "start-task": _handle_start_task,
        "do-next": _handle_do_next,
        "validate": _handle_validate,
        "close-task": _handle_close_task,
    }
