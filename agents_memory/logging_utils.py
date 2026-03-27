from __future__ import annotations

import logging
import os
from pathlib import Path


_CONFIGURED_LOGGERS: set[str] = set()


def _normalize_level(raw_level: str | None) -> int:
    level_name = str(raw_level or "INFO").strip().upper()
    return getattr(logging, level_name, logging.INFO)


def configure_logger(name: str, *, base_dir: Path) -> logging.Logger:
    # Build a rotating-file logger writing to <base_dir>/logs/<name>.log.
    """Create a process-safe file logger shared by CLI and MCP server."""
    logs_dir = base_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "agents-memory.log"

    logger = logging.getLogger(name)
    if name in _CONFIGURED_LOGGERS:
        return logger

    level = _normalize_level(os.getenv("AGENTS_MEMORY_LOG_LEVEL"))
    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if os.getenv("AGENTS_MEMORY_LOG_STDERR", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(level)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    _CONFIGURED_LOGGERS.add(name)
    logger.debug("logger configured | file=%s | level=%s", log_file, logging.getLevelName(level))
    return logger


def log_file_update(logger: logging.Logger, *, action: str, path: Path, detail: str = "") -> None:
    message = f"file_update | action={action} | path={path}"
    if detail:
        message += f" | detail={detail}"
    logger.info(message)
