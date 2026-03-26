from __future__ import annotations

from agents_memory.services.records import cmd_archive, cmd_list, cmd_new, cmd_promote, cmd_search, cmd_stats, cmd_update_index


def register() -> dict[str, callable]:
    return {
        "list": lambda ctx, args: cmd_list(ctx),
        "stats": lambda ctx, args: cmd_stats(ctx),
        "search": lambda ctx, args: cmd_search(ctx, " ".join(args)),
        "promote": lambda ctx, args: cmd_promote(ctx, args[0]) if args else print("用法: python3 memory.py promote <id>"),
        "archive": lambda ctx, args: cmd_archive(ctx),
        "update-index": lambda ctx, args: cmd_update_index(ctx),
        "new": lambda ctx, args: cmd_new(ctx),
    }
