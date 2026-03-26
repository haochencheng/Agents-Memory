from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from agents_memory.runtime import build_context


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class RuntimeBootstrapTests(unittest.TestCase):
    def test_build_context_bootstraps_local_runtime_files_from_templates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_text(root / "templates" / "index.example.md", "index template\n")
            _write_text(root / "templates" / "projects.example.md", "projects template\n")
            _write_text(root / "templates" / "rules.example.md", "rules template\n")

            previous_root = os.environ.get("AGENTS_MEMORY_ROOT")
            os.environ["AGENTS_MEMORY_ROOT"] = str(root)
            try:
                ctx = build_context(logger_name="tests.runtime.bootstrap", reference_file=__file__)
            finally:
                if previous_root is None:
                    os.environ.pop("AGENTS_MEMORY_ROOT", None)
                else:
                    os.environ["AGENTS_MEMORY_ROOT"] = previous_root

            self.assertTrue(ctx.errors_dir.exists())
            self.assertTrue(ctx.archive_dir.exists())
            self.assertTrue(ctx.memory_dir.exists())
            self.assertEqual(ctx.index_file.read_text(encoding="utf-8"), "index template\n")
            self.assertEqual(ctx.projects_file.read_text(encoding="utf-8"), "projects template\n")
            self.assertEqual(ctx.rules_file.read_text(encoding="utf-8"), "rules template\n")