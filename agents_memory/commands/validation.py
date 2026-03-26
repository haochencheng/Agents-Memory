from __future__ import annotations

from agents_memory.services.validation import cmd_docs_check


def _handle_docs_check(ctx, args: list[str]) -> None:
    target = "."
    strict = False
    output_format = "text"
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--strict":
            strict = True
        elif arg == "--format" and index + 1 < len(args):
            output_format = args[index + 1]
            index += 1
        elif not arg.startswith("--"):
            target = arg
        index += 1

    raise SystemExit(cmd_docs_check(ctx, target, strict=strict, output_format=output_format))


def register() -> dict[str, callable]:
    return {
        "docs-check": _handle_docs_check,
    }