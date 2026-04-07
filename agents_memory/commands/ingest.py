from __future__ import annotations

from collections.abc import Callable

from agents_memory.services.ingest import cmd_ingest


def _handle_ingest(ctx, args: list[str]) -> None:
    raise SystemExit(cmd_ingest(ctx, args))


def register() -> dict[str, Callable]:
    return {
        "ingest": _handle_ingest,
    }
