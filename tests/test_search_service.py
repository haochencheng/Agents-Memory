from __future__ import annotations

import os
import tempfile
import textwrap
import unittest
from pathlib import Path

from agents_memory.runtime import build_context
from agents_memory.services.search import search_knowledge_hybrid, search_knowledge_semantic


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
        return build_context(logger_name=f"tests.search.{root.name}", reference_file=__file__)
    finally:
        if previous_root is None:
            os.environ.pop("AGENTS_MEMORY_ROOT", None)
        else:
            os.environ["AGENTS_MEMORY_ROOT"] = previous_root


class SearchServiceTests(unittest.TestCase):
    def test_semantic_search_returns_related_wiki_and_workflow_docs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _ctx(root)
            _write(
                root / "memory" / "wiki" / "auth-design.md",
                textwrap.dedent("""\
                    ---
                    topic: auth-design
                    project: synapse-network
                    source_path: docs/architecture/auth-design.md
                    doc_type: architecture
                    tags: [auth, jwt, redis]
                    ---

                    # Auth Design

                    Refresh tokens are issued by AuthService and persisted in RedisTokenStore.
                """),
            )
            _write(
                root / "memory" / "workflow_records" / "TASK-77.md",
                textwrap.dedent("""\
                    ---
                    id: TASK-77
                    title: "Roll out refresh token storage"
                    project: synapse-network
                    source_type: task_completion
                    status: completed
                    created_at: 2026-04-13
                    ---

                    Implement RedisTokenStore handling for AuthService token refresh.
                """),
            )

            results = search_knowledge_semantic(ctx, "redis token refresh", limit=10)
            ids = [item["id"] for item in results]

            self.assertIn("auth-design", ids)
            self.assertIn("TASK-77", ids)

    def test_hybrid_search_merges_fts_and_semantic_scores(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _ctx(root)
            _write(
                root / "memory" / "wiki" / "billing-recharge.md",
                textwrap.dedent("""\
                    ---
                    topic: billing-recharge
                    project: synapse-network
                    source_path: docs/billing/recharge.md
                    doc_type: guide
                    tags: [billing, recharge]
                    ---

                    # Billing Recharge

                    Recharge success updates balance and writes the settlement event.
                """),
            )

            results = search_knowledge_hybrid(ctx, "billing recharge settlement", limit=5, source_kind="wiki")

            self.assertEqual(results[0]["id"], "billing-recharge")
            self.assertGreater(results[0]["combined_score"], 0.0)
            self.assertGreater(results[0]["semantic_score"], 0.0)
            self.assertGreater(results[0]["fts_score"], 0.0)
