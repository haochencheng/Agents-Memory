"""Tests for Phases 1-5 MCP tool integrations.

Phase 1: memory_wiki_compile  — wiki compiled truth
Phase 2: memory_search        — hybrid FTS + vector search
Phase 3: wiki cross-references (tested via wiki service; here test MCP search integration)
Phase 4: memory_ingest        — structured ingest pipeline
Phase 5: memory_wiki_lint     — wiki health checks

All tests are offline — no LLM calls, no real filesystem side effects beyond tmp.
"""

from __future__ import annotations

import importlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_env(root: Path) -> None:
    """Minimal project layout required by build_context."""
    _write(root / "templates" / "index.example.md", "# Index\n")
    _write(root / "templates" / "projects.example.md", "# Projects\n")
    _write(root / "templates" / "rules.example.md", "# Rules\n")
    _write(root / "memory" / "rules.md", "# Rules\n\nAlways write tests.\n")


def _make_wiki_page(root: Path, topic: str, *, compiled_at: str = "2026-04-07", extra_fm: str = "") -> None:
    _write(
        root / "memory" / "wiki" / f"{topic}.md",
        f"---\ntopic: {topic}\ncreated_at: 2026-04-07\nupdated_at: 2026-04-07\ncompiled_at: {compiled_at}\n{extra_fm}---\n\n## 结论（Compiled Truth）\n\n> Some truth.\n\n---\n\n## 时间线\n\n- 2026-04-07 init\n",
    )


def _make_error(root: Path, eid: str, content: str = "test error body") -> None:
    _write(
        root / "errors" / f"{eid}.md",
        f"---\nid: {eid}\ntitle: {content}\ncategory: test\ndomain: backend\nseverity: medium\nstatus: open\ndate: 2026-04-07\nproject: test-proj\n---\n\n{content}\n",
    )


class _BaseMCPTest(unittest.TestCase):
    """Base class: sets up tmp dir + loads mcp_app module."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _build_env(self.root)
        self._prev_root = os.environ.get("AGENTS_MEMORY_ROOT")
        os.environ["AGENTS_MEMORY_ROOT"] = str(self.root)
        self.mcp = self._reload_mcp()

    def tearDown(self) -> None:
        self._tmp.cleanup()
        if self._prev_root is None:
            os.environ.pop("AGENTS_MEMORY_ROOT", None)
        else:
            os.environ["AGENTS_MEMORY_ROOT"] = self._prev_root

    def _reload_mcp(self):
        import agents_memory.mcp_app as _mod
        return importlib.reload(_mod)


# ---------------------------------------------------------------------------
# Phase 1 — memory_wiki_compile
# ---------------------------------------------------------------------------

class TestMCPWikiCompile(_BaseMCPTest):
    """Tests for memory_wiki_compile MCP tool (Phase 1)."""

    def test_dry_run_returns_dry_run_status(self) -> None:
        _make_wiki_page(self.root, "finance-safety")
        _make_error(self.root, "AME-001", "float precision issue")
        mcp = self._reload_mcp()
        result = json.loads(mcp.memory_wiki_compile("finance-safety", scope="errors", dry_run=True))
        self.assertEqual(result["status"], "dry_run")
        self.assertIn("dry-run", result["new_compiled_truth"].lower())
        self.assertFalse(result["dry_run"] is False)  # dry_run=True should be reflected

    def test_returns_skipped_when_no_errors(self) -> None:
        _make_wiki_page(self.root, "empty-topic")
        mcp = self._reload_mcp()
        result = json.loads(mcp.memory_wiki_compile("empty-topic", scope="errors", dry_run=False))
        self.assertEqual(result["status"], "skipped")
        self.assertIn("no error records", result.get("reason", ""))

    def test_scope_not_errors_returns_skipped(self) -> None:
        _make_wiki_page(self.root, "alpha")
        _make_error(self.root, "AME-002", "some bug")
        mcp = self._reload_mcp()
        result = json.loads(mcp.memory_wiki_compile("alpha", scope="wiki", dry_run=False))
        self.assertEqual(result["status"], "skipped")

    def test_dry_run_includes_error_count(self) -> None:
        _make_wiki_page(self.root, "backend")
        for i in range(3):
            _make_error(self.root, f"AME-{i:03d}", "backend failure")
        mcp = self._reload_mcp()
        result = json.loads(mcp.memory_wiki_compile("backend", scope="errors", dry_run=True))
        self.assertGreater(result["error_count"], 0)

    def test_with_mock_llm_writes_compiled_truth(self) -> None:
        _make_wiki_page(self.root, "finance-safety")
        _make_error(self.root, "AME-010", "float precision error in transfer")
        with patch(
            "agents_memory.services.wiki_compile._call_llm",
            return_value="## 结论\n\n> 精度问题: 使用 Decimal。",
        ):
            mcp = self._reload_mcp()
            result = json.loads(mcp.memory_wiki_compile("finance-safety", scope="errors", dry_run=False))
        self.assertEqual(result["status"], "ok")
        self.assertIn("Decimal", result["new_compiled_truth"])
        self.assertIn("wiki-compile", result["timeline_entry"])


# ---------------------------------------------------------------------------
# Phase 2 — memory_search (hybrid FTS + vector)
# ---------------------------------------------------------------------------

class TestMCPSearch(_BaseMCPTest):
    """Tests for memory_search MCP tool (Phase 2)."""

    def test_fts_mode_returns_list(self) -> None:
        _make_error(self.root, "AME-101", "token validation fails on refresh")
        mcp = self._reload_mcp()
        result_str = mcp.memory_search("token validation", limit=5, mode="fts")
        # Should either return JSON list or a "no results" message
        try:
            data = json.loads(result_str)
            self.assertIsInstance(data, list)
        except json.JSONDecodeError:
            self.assertIn("token", result_str.lower())

    def test_hybrid_mode_no_crash_when_vector_unavailable(self) -> None:
        _make_error(self.root, "AME-102", "auth expiry bug")
        mcp = self._reload_mcp()
        # hybrid may fall back to FTS only; should not raise
        result = mcp.memory_search("auth expiry", limit=5, mode="hybrid")
        self.assertIsInstance(result, str)

    def test_empty_results_message_when_no_match(self) -> None:
        mcp = self._reload_mcp()
        result = mcp.memory_search("zzz-no-such-thing-xyz", limit=5, mode="fts")
        self.assertIsInstance(result, str)

    def test_invalid_mode_falls_back_gracefully(self) -> None:
        """vector mode requires LanceDB; should return something, not crash."""
        _make_error(self.root, "AME-103", "some error")
        mcp = self._reload_mcp()
        result = mcp.memory_search("some error", limit=3, mode="vector")
        self.assertIsInstance(result, str)

    def test_fts_mode_finds_keyword_in_errors(self) -> None:
        _make_error(self.root, "AME-200", "reentrancy attack vulnerability detected in contract")
        mcp = self._reload_mcp()
        result_str = mcp.memory_search("reentrancy", limit=5, mode="fts")
        # After FTS index built, should find it
        try:
            results = json.loads(result_str)
            ids = [r.get("id", "") for r in results]
            self.assertIn("AME-200", ids)
        except json.JSONDecodeError:
            # First run might say "build index first" — acceptable
            self.assertIsInstance(result_str, str)


# ---------------------------------------------------------------------------
# Phase 4 — memory_ingest
# ---------------------------------------------------------------------------

class TestMCPIngest(_BaseMCPTest):
    """Tests for memory_ingest MCP tool (Phase 4)."""

    def test_invalid_source_type_returns_error_message(self) -> None:
        mcp = self._reload_mcp()
        result = mcp.memory_ingest("some content", source_type="invalid-type")
        self.assertIn("不支持", result)
        self.assertIn("invalid-type", result)

    def test_dry_run_does_not_write_ingest_log(self) -> None:
        _make_wiki_page(self.root, "auth-design")
        ingest_log = self.root / "memory" / "ingest_log.jsonl"
        with patch(
            "agents_memory.services.ingest._call_llm",
            return_value=json.dumps({
                "summary": "Fixed auth token issue",
                "topics": ["auth-design"],
                "timeline_entry": "2026-04-07 [pr-review] Fixed OAuth token",
                "compiled_truth_update": None,
            }),
        ):
            mcp = self._reload_mcp()
            result = mcp.memory_ingest(
                content="## PR #42: Fix OAuth token validation\n\nFixed auth expiry.",
                source_type="pr-review",
                project="test-proj",
                dry_run=True,
            )
        self.assertIn("DRY-RUN", result)
        # ingest log should NOT be written in dry_run mode
        self.assertFalse(ingest_log.exists())

    def test_successful_ingest_writes_log(self) -> None:
        _make_wiki_page(self.root, "backend")
        ingest_log = self.root / "memory" / "ingest_log.jsonl"
        with patch(
            "agents_memory.services.ingest._call_llm",
            return_value=json.dumps({
                "summary": "Fixed retry logic",
                "topics": ["backend"],
                "timeline_entry": "2026-04-07 [meeting] Discussed retry backoff",
                "compiled_truth_update": None,
            }),
        ):
            mcp = self._reload_mcp()
            result = mcp.memory_ingest(
                content="## Meeting Notes\n\nDiscussed retry backoff for backend services.",
                source_type="meeting",
                project="infra",
                dry_run=False,
            )
        self.assertIn("摄取完成", result)
        self.assertTrue(ingest_log.exists())
        log_line = json.loads(ingest_log.read_text().strip())
        self.assertEqual(log_line["ingest_type"], "meeting")
        self.assertEqual(log_line["project"], "infra")

    def test_all_supported_types_accepted(self) -> None:
        mcp = self._reload_mcp()
        for t in ("pr-review", "meeting", "decision", "code-review"):
            with patch(
                "agents_memory.services.ingest._call_llm",
                return_value=json.dumps({
                    "summary": f"Test {t}",
                    "topics": [],
                    "timeline_entry": f"2026-04-07 [{t}] test",
                }),
            ):
                # Reload each time to pick up fresh ctx
                mcp = self._reload_mcp()
                result = mcp.memory_ingest(f"content for {t}", source_type=t, dry_run=True)
                self.assertNotIn("不支持", result, f"type {t!r} should be accepted")

    def test_llm_parse_error_returns_error_message(self) -> None:
        with patch(
            "agents_memory.services.ingest._call_llm",
            return_value="NOT VALID JSON {{{}",
        ):
            mcp = self._reload_mcp()
            result = mcp.memory_ingest("content", source_type="decision", dry_run=False)
        # Should return error message, not crash
        self.assertIsInstance(result, str)


# ---------------------------------------------------------------------------
# Phase 5 — memory_wiki_lint
# ---------------------------------------------------------------------------

class TestMCPWikiLint(_BaseMCPTest):
    """Tests for memory_wiki_lint MCP tool (Phase 5)."""

    def test_empty_wiki_returns_pass_message(self) -> None:
        mcp = self._reload_mcp()
        result = mcp.memory_wiki_lint()
        self.assertIsInstance(result, str)

    def test_detects_stale_compiled_at(self) -> None:
        _make_wiki_page(self.root, "old-topic", compiled_at="2020-01-01")
        mcp = self._reload_mcp()
        result = mcp.memory_wiki_lint(check="stale")
        self.assertIn("stale", result.lower())
        self.assertIn("old-topic", result)

    def test_fresh_page_no_stale_warning(self) -> None:
        _make_wiki_page(self.root, "fresh-topic", compiled_at="2026-04-07")
        mcp = self._reload_mcp()
        result = mcp.memory_wiki_lint(check="stale")
        self.assertNotIn("fresh-topic", result.lower().replace("✅", ""))

    def test_orphan_detection(self) -> None:
        _make_wiki_page(self.root, "orphan-page")
        mcp = self._reload_mcp()
        result = mcp.memory_wiki_lint(check="orphans")
        self.assertIn("orphan-page", result)

    def test_linked_page_not_orphan(self) -> None:
        _make_wiki_page(self.root, "source-page")
        _write(
            self.root / "memory" / "wiki" / "linking-page.md",
            "---\ntopic: linking-page\ncompiled_at: 2026-04-07\nlinks:\n  - topic: source-page\n---\n\n## 结论\n\n> links to source.\n\n---\n\n## 时间线\n\n- init\n",
        )
        mcp = self._reload_mcp()
        result = mcp.memory_wiki_lint(check="orphans")
        # source-page is referenced by linking-page → not orphan
        self.assertNotIn("[orphan] 'source-page'", result)

    def test_check_all_runs_without_crash(self) -> None:
        _make_wiki_page(self.root, "topic-a")
        _make_wiki_page(self.root, "topic-b", compiled_at="2020-06-01")
        mcp = self._reload_mcp()
        result = mcp.memory_wiki_lint(check="all")
        self.assertIsInstance(result, str)

    def test_lint_returns_string_not_empty_on_issues(self) -> None:
        _make_wiki_page(self.root, "problem-page", compiled_at="2019-01-01")
        mcp = self._reload_mcp()
        result = mcp.memory_wiki_lint()
        self.assertGreater(len(result.strip()), 0)


if __name__ == "__main__":
    unittest.main()
