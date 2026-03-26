from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from agents_memory.runtime import build_context
from agents_memory.services.validation import cmd_docs_check, collect_docs_check_findings


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class DocsCheckTests(unittest.TestCase):
    def _build_context(self, root: Path):
        _write_text(root / "templates" / "index.example.md", "index\n")
        _write_text(root / "templates" / "projects.example.md", "# Project Registry\n")
        _write_text(root / "templates" / "rules.example.md", "# Promoted Rules\n")
        previous_root = os.environ.get("AGENTS_MEMORY_ROOT")
        os.environ["AGENTS_MEMORY_ROOT"] = str(root)
        try:
            return build_context(logger_name=f"tests.docs_check.{root.name}", reference_file=__file__)
        finally:
            if previous_root is None:
                os.environ.pop("AGENTS_MEMORY_ROOT", None)
            else:
                os.environ["AGENTS_MEMORY_ROOT"] = previous_root

    def test_collect_docs_check_findings_flags_missing_docs_index_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_text(root / "README.md", "# Demo\n")
            _write_text(root / "docs" / "README.md", "- [Missing](missing.md)\n")
            _write_text(root / "docs" / "getting-started.md", "python3 scripts/memory.py new\n")
            _write_text(root / "llms.txt", "python3 scripts/memory.py new\n")

            findings = collect_docs_check_findings(root)

            self.assertTrue(any(f.status == "FAIL" and f.key == "docs_readme_links" for f in findings))

    def test_cmd_docs_check_returns_zero_for_minimal_healthy_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = self._build_context(root)
            _write_text(root / "README.md", "# Demo\n")
            _write_text(root / "docs" / "README.md", "- [Getting Started](getting-started.md)\n- [Ops](ops.md)\n")
            _write_text(
                root / "docs" / "getting-started.md",
                "\n".join(
                    [
                        "python3 scripts/memory.py new",
                        "python3 scripts/memory.py list",
                        "python3 scripts/memory.py stats",
                        "python3 scripts/memory.py search foo",
                        "python3 scripts/memory.py embed",
                        "python3 scripts/memory.py vsearch foo",
                        "python3 scripts/memory.py promote 2026-03-26-other-001",
                        "python3 scripts/memory.py sync",
                        "python3 scripts/memory.py bridge-install demo",
                        "python3 scripts/memory.py copilot-setup demo",
                        "python3 scripts/memory.py agent-list",
                        "python3 scripts/memory.py agent-setup github-copilot .",
                        "python3 scripts/memory.py register .",
                        "python3 scripts/memory.py mcp-setup demo",
                        "python3 scripts/memory.py doctor demo",
                        "python3 scripts/memory.py docs-check .",
                        "python3 scripts/memory.py archive",
                        "python3 scripts/memory.py update-index",
                        "python3 scripts/memory.py to-qdrant",
                    ]
                ),
            )
            _write_text(root / "docs" / "ops.md", "# Ops\n")
            _write_text(
                root / "llms.txt",
                "\n".join(
                    [
                        "python3 scripts/memory.py new",
                        "python3 scripts/memory.py list",
                        "python3 scripts/memory.py stats",
                        "python3 scripts/memory.py search <keyword>",
                        "python3 scripts/memory.py embed",
                        "python3 scripts/memory.py vsearch <query>",
                        "python3 scripts/memory.py promote <id>",
                        "python3 scripts/memory.py sync",
                        "python3 scripts/memory.py bridge-install <project-id>",
                        "python3 scripts/memory.py copilot-setup [project-id]",
                        "python3 scripts/memory.py agent-list",
                        "python3 scripts/memory.py agent-setup <agent> [path]",
                        "python3 scripts/memory.py register [path]",
                        "python3 scripts/memory.py mcp-setup [project-id]",
                        "python3 scripts/memory.py doctor [project-id]",
                        "python3 scripts/memory.py docs-check [path]",
                        "python3 scripts/memory.py archive",
                        "python3 scripts/memory.py to-qdrant",
                        "python3 scripts/memory.py update-index",
                    ]
                ),
            )

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = cmd_docs_check(ctx, str(root))

            self.assertEqual(exit_code, 0)
            self.assertIn("Overall: OK", buffer.getvalue())