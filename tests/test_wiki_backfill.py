from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from agents_memory.runtime import build_context
from agents_memory.services.wiki import read_wiki_page
from agents_memory.services.wiki_backfill import backfill_wiki_metadata_and_links
from agents_memory.services.workflow_records import normalize_project_id


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _ctx(root: Path):
    _write(root / "templates" / "index.example.md", "# Index\n")
    _write(root / "templates" / "projects.example.md", "# Projects\n")
    _write(root / "templates" / "rules.example.md", "# Rules\n")
    previous_root = os.environ.get("AGENTS_MEMORY_ROOT")
    os.environ["AGENTS_MEMORY_ROOT"] = str(root)
    try:
        return build_context(logger_name=f"tests.wiki_backfill.{root.name}", reference_file=__file__)
    finally:
        if previous_root is None:
            os.environ.pop("AGENTS_MEMORY_ROOT", None)
        else:
            os.environ["AGENTS_MEMORY_ROOT"] = previous_root


class WikiBackfillTests(unittest.TestCase):
    def test_backfill_populates_metadata_and_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _ctx(root)
            _write(
                root / "memory" / "wiki" / "synapse-network-readme.md",
                "---\ntopic: synapse-network-readme\n---\n\n# README\n",
            )
            _write(
                root / "memory" / "wiki" / "synapse-network-docs-billing-recharge.md",
                "---\ntopic: synapse-network-docs-billing-recharge\n---\n\n# Billing Recharge\n",
            )
            _write(
                root / "memory" / "wiki" / "synapse-network-docs-billing-refund.md",
                "---\ntopic: synapse-network-docs-billing-refund\n---\n\n# Billing Refund\n",
            )

            result = backfill_wiki_metadata_and_links(ctx)
            self.assertEqual(result.updated, 3)

            readme = read_wiki_page(ctx.wiki_dir, "synapse-network-readme")
            self.assertIsNotNone(readme)
            assert readme is not None
            self.assertIn("project: synapse-network", readme)
            self.assertIn("source_path: README.md", readme)
            self.assertIn("doc_type: root-doc", readme)

            refund = read_wiki_page(ctx.wiki_dir, "synapse-network-docs-billing-refund")
            self.assertIsNotNone(refund)
            assert refund is not None
            self.assertIn("source_path: docs/billing/refund.md", refund)
            self.assertIn("links:", refund)
            self.assertIn("topic: synapse-network-docs-billing-recharge", refund)

    def test_backfill_uses_legacy_sources_field_for_source_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _ctx(root)
            _write(
                root / "memory" / "wiki" / "agents-memory-web-api.md",
                "---\n"
                "topic: agents-memory-web-api\n"
                "sources: [docs/frontend/03-api-contract.md]\n"
                "---\n\n"
                "# Agents-Memory Web API\n",
            )

            result = backfill_wiki_metadata_and_links(ctx)
            self.assertEqual(result.updated, 1)
            self.assertEqual(result.items[0].doc_type, "frontend")

            page = read_wiki_page(ctx.wiki_dir, "agents-memory-web-api")
            self.assertIsNotNone(page)
            assert page is not None
            self.assertIn(f"project: {normalize_project_id(root.name)}", page)
            self.assertIn("source_path: docs/frontend/03-api-contract.md", page)
            self.assertIn("doc_type: frontend", page)

    def test_backfill_detects_architecture_and_maintenance_from_root_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _ctx(root)
            _write(
                root / "memory" / "wiki" / "synapse-architecture.md",
                "---\n"
                "topic: synapse-architecture\n"
                "sources: [ARCHITECTURE.md]\n"
                "---\n\n"
                "# Synapse Architecture\n",
            )
            _write(
                root / "memory" / "wiki" / "synapse-bugfix-frontend.md",
                "---\n"
                "topic: synapse-bugfix-frontend\n"
                "sources: [BUG-FRONTEND-01-404-routes.md]\n"
                "---\n\n"
                "# Bug Frontend 404 Routes Failed\n",
            )

            result = backfill_wiki_metadata_and_links(ctx)
            self.assertEqual(result.updated, 2)

            page_map = {item.topic: item for item in result.items}
            self.assertEqual(page_map["synapse-architecture"].doc_type, "architecture")
            self.assertEqual(page_map["synapse-bugfix-frontend"].doc_type, "maintenance")

    def test_backfill_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _ctx(root)
            topic_path = root / "memory" / "wiki" / "synapse-network-readme.md"
            _write(topic_path, "---\ntopic: synapse-network-readme\n---\n\n# README\n")

            before = topic_path.read_text(encoding="utf-8")
            result = backfill_wiki_metadata_and_links(ctx, dry_run=True)
            after = topic_path.read_text(encoding="utf-8")

            self.assertEqual(result.updated, 1)
            self.assertEqual(before, after)
