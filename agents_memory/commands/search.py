from __future__ import annotations

from collections.abc import Callable

from agents_memory.services.search import cmd_fts_index, cmd_hybrid_search


def _handle_fts_index(ctx, args: list[str]) -> None:
    raise SystemExit(cmd_fts_index(ctx, args))


def _handle_hybrid_search(ctx, args: list[str]) -> None:
    raise SystemExit(cmd_hybrid_search(ctx, args))


def register() -> dict[str, Callable]:
    return {
        "fts-index": _handle_fts_index,
        "hybrid-search": _handle_hybrid_search,
    }
