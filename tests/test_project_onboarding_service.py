from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from agents_memory.runtime import build_context
from agents_memory.services.project_onboarding import discover_project_wiki_sources, ingest_project_wiki_sources
from agents_memory.services.wiki import read_wiki_page


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_context(root: Path):
    _write_text(root / "templates" / "index.example.md", "index\n")
    _write_text(root / "templates" / "projects.example.md", "# Project Registry\n")
    _write_text(root / "templates" / "rules.example.md", "# Rules\n")
    previous_root = os.environ.get("AGENTS_MEMORY_ROOT")
    os.environ["AGENTS_MEMORY_ROOT"] = str(root)
    try:
        return build_context(logger_name=f"tests.project_onboarding.{root.name}", reference_file=__file__)
    finally:
        if previous_root is None:
            os.environ.pop("AGENTS_MEMORY_ROOT", None)
        else:
            os.environ["AGENTS_MEMORY_ROOT"] = previous_root


class ProjectOnboardingServiceTests(unittest.TestCase):
    def test_discover_project_wiki_sources_prefers_docs_corpus_and_includes_plans(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "Synapse-Network"
            project_root.mkdir(parents=True)
            _write_text(project_root / "README.md", "# README\n")
            _write_text(project_root / "AGENTS.md", "# Agents\n")
            _write_text(project_root / "docs" / "architecture.md", "# Architecture\n")
            _write_text(project_root / "docs" / "plans" / "plan.md", "# Keep me\n")
            _write_text(project_root / "services" / "gateway" / "README.md", "# Service README\n")
            _write_text(project_root / ".pytest_cache" / "README.md", "# Ignore cache\n")
            _write_text(project_root / ".github" / "instructions" / "agents-memory" / "ignored.md", "# Ignore me too\n")

            discovered = discover_project_wiki_sources(project_root)
            relative = [path.relative_to(project_root).as_posix() for path in discovered]

            self.assertEqual(relative[:2], ["README.md", "AGENTS.md"])
            self.assertIn("docs/architecture.md", relative)
            self.assertIn("docs/plans/plan.md", relative)
            self.assertNotIn("services/gateway/README.md", relative)
            self.assertNotIn(".pytest_cache/README.md", relative)
            self.assertNotIn(".github/instructions/agents-memory/ignored.md", relative)

    def test_ingest_project_wiki_sources_writes_project_metadata_and_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_context(root)
            project_root = root / "Synapse-Network"
            project_root.mkdir(parents=True)
            _write_text(project_root / "README.md", "# Synapse\n")
            _write_text(project_root / "docs" / "architecture.md", "# Architecture\n")

            result = ingest_project_wiki_sources(ctx, project_root, max_files=10)

            self.assertEqual(result.project_id, "synapse-network")
            self.assertEqual(result.ingested_count, 2)
            self.assertEqual(len(result.sources), 2)

            readme_page = read_wiki_page(ctx.wiki_dir, "synapse-network-readme")
            self.assertIsNotNone(readme_page)
            assert readme_page is not None
            self.assertIn("project: synapse-network", readme_page)
            self.assertIn("source_path: README.md", readme_page)
            self.assertIn("doc_type: root-doc", readme_page)
            self.assertIn("tags: [synapse-network]", readme_page)

            architecture_page = read_wiki_page(ctx.wiki_dir, "synapse-network-docs-architecture")
            self.assertIsNotNone(architecture_page)
            assert architecture_page is not None
            self.assertIn("doc_type: docs-root", architecture_page)
            self.assertIn("tags: [synapse-network]", architecture_page)

            log_path = root / "memory" / "ingest_log.jsonl"
            lines = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(lines[0]["source_type"], "project_wiki")
            self.assertEqual(lines[0]["project"], "synapse-network")

    def test_ingest_project_wiki_sources_generates_candidate_links_for_related_docs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_context(root)
            project_root = root / "Synapse-Network"
            project_root.mkdir(parents=True)
            _write_text(project_root / "docs" / "billing" / "recharge.md", "# Recharge\n")
            _write_text(project_root / "docs" / "billing" / "refund.md", "# Refund\n")

            ingest_project_wiki_sources(ctx, project_root, max_files=10)

            refund_page = read_wiki_page(ctx.wiki_dir, "synapse-network-docs-billing-refund")
            self.assertIsNotNone(refund_page)
            assert refund_page is not None
            self.assertIn("links:", refund_page)
            self.assertIn("topic: synapse-network-docs-billing-recharge", refund_page)

    def test_ingest_project_wiki_sources_extracts_explicit_markdown_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_context(root)
            project_root = root / "Synapse-Network"
            project_root.mkdir(parents=True)
            _write_text(project_root / "docs" / "architecture.md", "# Architecture\n")
            _write_text(
                project_root / "docs" / "guides" / "getting-started.md",
                "# Getting Started\n\nSee [Architecture](../architecture.md) before changing flows.\n",
            )

            ingest_project_wiki_sources(ctx, project_root, max_files=10)

            guide_page = read_wiki_page(ctx.wiki_dir, "synapse-network-docs-guides-getting-started")
            self.assertIsNotNone(guide_page)
            assert guide_page is not None
            self.assertIn("topic: synapse-network-docs-architecture", guide_page)
            self.assertIn("context: \"正文引用: docs/architecture.md\"", guide_page)

    def test_discover_project_wiki_sources_applies_optional_limit_to_docs_corpus(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "Synapse-Network"
            project_root.mkdir(parents=True)
            _write_text(project_root / "README.md", "# README\n")
            _write_text(project_root / "AGENTS.md", "# Agents\n")
            _write_text(project_root / "docs" / "a.md", "# A\n")
            _write_text(project_root / "docs" / "b.md", "# B\n")

            discovered = discover_project_wiki_sources(project_root, max_files=3)
            relative = [path.relative_to(project_root).as_posix() for path in discovered]

            self.assertEqual(relative, ["README.md", "AGENTS.md", "docs/a.md"])
