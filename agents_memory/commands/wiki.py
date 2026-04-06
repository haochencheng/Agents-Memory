from __future__ import annotations

from collections.abc import Callable

from agents_memory.services.wiki import cmd_wiki_ingest, cmd_wiki_list, cmd_wiki_query, cmd_wiki_sync


def _handle_wiki_list(ctx, args: list[str]) -> None:
    raise SystemExit(cmd_wiki_list(ctx, args))


def _handle_wiki_query(ctx, args: list[str]) -> None:
    raise SystemExit(cmd_wiki_query(ctx, args))


def _handle_wiki_ingest(ctx, args: list[str]) -> None:
    raise SystemExit(cmd_wiki_ingest(ctx, args))


def _handle_wiki_sync(ctx, args: list[str]) -> None:
    raise SystemExit(cmd_wiki_sync(ctx, args))


def register() -> dict[str, Callable]:
    return {
        "wiki-list": _handle_wiki_list,
        "wiki-query": _handle_wiki_query,
        "wiki-ingest": _handle_wiki_ingest,
        "wiki-sync": _handle_wiki_sync,
    }
