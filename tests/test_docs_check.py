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

    def test_collect_docs_check_findings_flags_missing_contract_docs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_text(root / "README.md", "# Demo\n")
            _write_text(root / "docs" / "README.md", "- [Getting Started](getting-started.md)\n")
            _write_text(root / "docs" / "getting-started.md", "python3 scripts/memory.py new\n")
            _write_text(root / "llms.txt", "python3 scripts/memory.py new\n")

            findings = collect_docs_check_findings(root)

            self.assertTrue(any(f.status == "FAIL" and f.key == "contract_files" for f in findings))

    def test_collect_docs_check_findings_flags_missing_policy_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_text(root / "README.md", "# Demo\n")
            _write_text(root / "docs" / "README.md", "- [Getting Started](getting-started.md)\n")
            _write_text(root / "docs" / "getting-started.md", "python3 scripts/memory.py new\n")
            _write_text(root / "docs" / "ai-engineering-operating-system.md", "Shared Engineering Brain\nMemory\nStandards\nPlanning\nValidation\n")
            _write_text(root / "docs" / "foundation-hardening.md", "Behavior change\n=> code change\n=> docs change\n=> test or validation change\n")
            _write_text(root / "llms.txt", "python3 scripts/memory.py new\n")
            (root / "tests").mkdir(parents=True, exist_ok=True)

            findings = collect_docs_check_findings(root)

            self.assertTrue(any(f.status == "FAIL" and f.key == "policy_files" for f in findings))

    def test_collect_docs_check_findings_flags_missing_open_source_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_text(root / "README.md", "# Demo\n")
            _write_text(root / "docs" / "README.md", "- [Getting Started](getting-started.md)\n")
            _write_text(root / "docs" / "getting-started.md", "python3 scripts/memory.py new\n")
            _write_text(root / "docs" / "ai-engineering-operating-system.md", "Shared Engineering Brain\nMemory\nStandards\nPlanning\nValidation\n")
            _write_text(root / "docs" / "foundation-hardening.md", "Behavior change\n=> code change\n=> docs change\n=> test or validation change\n")
            _write_text(root / "llms.txt", "python3 scripts/memory.py new\n")
            (root / "tests").mkdir(parents=True, exist_ok=True)

            findings = collect_docs_check_findings(root)

            self.assertTrue(any(f.status == "FAIL" and f.key == "open_source_files" for f in findings))

    def test_cmd_docs_check_returns_zero_for_minimal_healthy_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = self._build_context(root)
            _write_text(root / "README.md", "# Demo\n")
            _write_text(root / "docs" / "README.md", "- [Getting Started](getting-started.md)\n- [Ops](ops.md)\n")
            _write_text(
                root / "docs" / "ai-engineering-operating-system.md",
                "\n".join(
                    [
                        "Shared Engineering Brain",
                        "Memory",
                        "Standards",
                        "Planning",
                        "Validation",
                    ]
                ),
            )
            _write_text(
                root / "docs" / "foundation-hardening.md",
                "\n".join(
                    [
                        "Behavior change",
                        "=> code change",
                        "=> docs change",
                        "=> test or validation change",
                    ]
                ),
            )
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
                        "python3 scripts/memory.py plan-init sample-task .",
                        "python3 scripts/memory.py plan-check .",
                        "python3 scripts/memory.py profile-list",
                        "python3 scripts/memory.py profile-show python-service",
                        "python3 scripts/memory.py profile-apply python-service .",
                        "python3 scripts/memory.py profile-diff python-service .",
                        "python3 scripts/memory.py standards-sync .",
                        "python3 scripts/memory.py profile-check .",
                        "python3 scripts/memory.py docs-check .",
                        "python3 scripts/memory.py archive",
                        "python3 scripts/memory.py update-index",
                        "python3 scripts/memory.py to-qdrant",
                        "python3.12 -m unittest discover -s tests -p 'test_*.py'",
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
                        "python3 scripts/memory.py plan-init <task-name> [path]",
                        "python3 scripts/memory.py plan-check [path]",
                        "python3 scripts/memory.py profile-list",
                        "python3 scripts/memory.py profile-show python-service",
                        "python3 scripts/memory.py profile-apply python-service .",
                        "python3 scripts/memory.py profile-diff python-service .",
                        "python3 scripts/memory.py standards-sync [path]",
                        "python3 scripts/memory.py profile-check .",
                        "python3 scripts/memory.py docs-check [path]",
                        "python3 scripts/memory.py archive",
                        "python3 scripts/memory.py to-qdrant",
                        "python3 scripts/memory.py update-index",
                        "python3.12 -m unittest discover -s tests -p 'test_*.py'",
                    ]
                ),
            )
            _write_text(root / "LICENSE", "MIT\n")
            _write_text(root / "CONTRIBUTING.md", "# Contributing\n")
            _write_text(
                root / "pyproject.toml",
                "\n".join(
                    [
                        "[project]",
                        "name = 'demo'",
                        "",
                        "[project.urls]",
                        'Repository = "https://example.com/repo"',
                        'Documentation = "https://example.com/docs"',
                        'Issues = "https://example.com/issues"',
                    ]
                ),
            )
            _write_text(
                root / "standards" / "docs" / "docs-sync.instructions.md",
                "docs\ncode\ntests\n",
            )
            _write_text(
                root / "standards" / "validation" / "docs-check.rules.md",
                "\n".join(
                    [
                        "docs entrypoint 完整",
                        "核心 services 有单元测试",
                        "行为变更必须同时看到 code diff、docs diff、test diff 中至少两层联动",
                    ]
                ),
            )
            _write_text(
                root / "standards" / "planning" / "harness-engineering.md",
                "docs、code、validation\nplan / task graph / validation route\n",
            )
            _write_text(
                root / "standards" / "planning" / "review-checklist.md",
                "docs / code / tests\n最小验证结果\n",
            )
            _write_text(
                root / "standards" / "planning" / "spec-kit.md",
                "spec-first\n验收标准必须可被测试或命令验证\n",
            )
            for test_file in [
                "test_runtime_bootstrap.py",
                "test_projects_service.py",
                "test_records_service.py",
                "test_integration_service.py",
                "test_planning_service.py",
                "test_docs_check.py",
            ]:
                _write_text(root / "tests" / test_file, "import unittest\n")

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = cmd_docs_check(ctx, str(root))

            self.assertEqual(exit_code, 0)
            self.assertIn("Overall: OK", buffer.getvalue())
