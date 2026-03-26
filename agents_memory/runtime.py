from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from agents_memory.logging_utils import configure_logger


BOOTSTRAP_TEMPLATES = {
    "index_file": "index.example.md",
    "projects_file": "projects.example.md",
    "rules_file": "rules.example.md",
}


@dataclass(frozen=True)
class AppContext:
    base_dir: Path
    errors_dir: Path
    archive_dir: Path
    memory_dir: Path
    vector_dir: Path
    index_file: Path
    projects_file: Path
    rules_file: Path
    templates_dir: Path
    logger_name: str = "agents_memory.cli"

    @property
    def logger(self):
        return configure_logger(self.logger_name, base_dir=self.base_dir)

    def ensure_storage_dirs(self) -> None:
        self.errors_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def bootstrap_runtime_files(self) -> None:
        for attr_name, template_name in BOOTSTRAP_TEMPLATES.items():
            target = getattr(self, attr_name)
            if target.exists():
                continue
            template_path = self.templates_dir / template_name
            if not template_path.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")


def detect_base_dir(reference_file: str | Path | None = None) -> Path:
    env_root = os.environ.get("AGENTS_MEMORY_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()

    if reference_file is not None:
        ref = Path(reference_file).resolve()
        if ref.name.endswith(".py"):
            for candidate in (ref.parent.parent, ref.parent.parent.parent):
                if (candidate / "scripts" / "memory.py").exists() or (candidate / "agents_memory").exists():
                    return candidate

    return Path(__file__).resolve().parent.parent


def build_context(*, logger_name: str = "agents_memory.cli", reference_file: str | Path | None = None) -> AppContext:
    base_dir = detect_base_dir(reference_file)
    ctx = AppContext(
        base_dir=base_dir,
        errors_dir=base_dir / "errors",
        archive_dir=base_dir / "errors" / "archive",
        memory_dir=base_dir / "memory",
        vector_dir=base_dir / "vectors",
        index_file=base_dir / "index.md",
        projects_file=base_dir / "memory" / "projects.md",
        rules_file=base_dir / "memory" / "rules.md",
        templates_dir=base_dir / "templates",
        logger_name=logger_name,
    )
    ctx.ensure_storage_dirs()
    ctx.bootstrap_runtime_files()
    return ctx
