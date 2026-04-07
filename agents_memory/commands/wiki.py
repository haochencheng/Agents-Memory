from __future__ import annotations

from collections.abc import Callable

from agents_memory.services.wiki import (
    cmd_wiki_backlinks,
    cmd_wiki_ingest,
    cmd_wiki_link,
    cmd_wiki_lint,
    cmd_wiki_list,
    cmd_wiki_query,
    cmd_wiki_sync,
)
from agents_memory.services.wiki_compile import cmd_wiki_compile


def _handle_wiki_list(ctx, args: list[str]) -> None:
    raise SystemExit(cmd_wiki_list(ctx, args))


def _handle_wiki_query(ctx, args: list[str]) -> None:
    raise SystemExit(cmd_wiki_query(ctx, args))


def _handle_wiki_ingest(ctx, args: list[str]) -> None:
    raise SystemExit(cmd_wiki_ingest(ctx, args))


def _handle_wiki_sync(ctx, args: list[str]) -> None:
    raise SystemExit(cmd_wiki_sync(ctx, args))


def _handle_wiki_compile(ctx, args: list[str]) -> None:
    raise SystemExit(cmd_wiki_compile(ctx, args))


def _handle_wiki_link(ctx, args: list[str]) -> None:
    raise SystemExit(cmd_wiki_link(ctx, args))


def _handle_wiki_backlinks(ctx, args: list[str]) -> None:
    raise SystemExit(cmd_wiki_backlinks(ctx, args))


def _handle_wiki_lint(ctx, args: list[str]) -> None:
    raise SystemExit(cmd_wiki_lint(ctx, args))


def register() -> dict[str, Callable]:
    return {
        "wiki-list": _handle_wiki_list,
        "wiki-query": _handle_wiki_query,
        "wiki-ingest": _handle_wiki_ingest,
        "wiki-sync": _handle_wiki_sync,
        "wiki-compile": _handle_wiki_compile,
        "wiki-link": _handle_wiki_link,
        "wiki-backlinks": _handle_wiki_backlinks,
        "wiki-lint": _handle_wiki_lint,
    }
