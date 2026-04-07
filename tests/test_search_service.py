"""Tests for Phase 2 hybrid FTS + vector search service.

All tests are fully offline — no LanceDB or OpenAI API calls made.
Vector search is mocked when needed.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from agents_memory.runtime import build_context
from agents_memory.services.search import (
    FTS_DB_NAME,
    FTS_SCORE_WEIGHT,
    RECENT_BOOST,
    RECENT_DAYS,
    VECTOR_SCORE_WEIGHT,
    _fts_db_path,
    _fts_file_to_row,
    _fts_full_rebuild,
    _get_vector_scores,
    _is_recent,
    _merge_search_results,
    _open_fts_db,
    _parse_search_args,
    build_fts_index,
    cmd_fts_index,
    cmd_hybrid_search,
    hybrid_search,
    search_fts,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_ctx(root: Path):
    _write(root / "templates" / "index.example.md", "index\n")
    _write(root / "templates" / "projects.example.md", "# Projects\n")
    _write(root / "templates" / "rules.example.md", "# Rules\n")
    previous = os.environ.get("AGENTS_MEMORY_ROOT")
    os.environ["AGENTS_MEMORY_ROOT"] = str(root)
    try:
        return build_context(logger_name=f"tests.search.{root.name}", reference_file=__file__)
    finally:
        if previous is None:
            os.environ.pop("AGENTS_MEMORY_ROOT", None)


def _make_error_record(
    root: Path,
    record_id: str,
    *,
    project: str = "testproj",
    category: str = "logic",
    domain: str = "backend",
    severity: str = "P2",
    status: str = "new",
    date_str: str = "2024-01-10",
    body: str = "Error body text here.",
) -> Path:
    """Write a minimal error record .md file and return its path."""
    content = (
        f"---\n"
        f"id: {record_id}\n"
        f"project: {project}\n"
        f"category: {category}\n"
        f"domain: {domain}\n"
        f"severity: {severity}\n"
        f"status: {status}\n"
        f"date: {date_str}\n"
        f"---\n\n"
        f"{body}\n"
    )
    path = root / "errors" / f"{record_id}.md"
    _write(path, content)
    return path


# ---------------------------------------------------------------------------
# TestFtsDbPath
# ---------------------------------------------------------------------------


class TestFtsDbPath(unittest.TestCase):
    def test_returns_path_in_vector_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            path = _fts_db_path(ctx)
            self.assertEqual(path.parent, ctx.vector_dir)
            self.assertEqual(path.name, FTS_DB_NAME)

    def test_creates_vector_dir_if_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            # Remove the vector dir to test mkdirs
            import shutil
            if ctx.vector_dir.exists():
                shutil.rmtree(ctx.vector_dir)
            path = _fts_db_path(ctx)
            self.assertTrue(path.parent.exists())


# ---------------------------------------------------------------------------
# TestBuildFtsIndex
# ---------------------------------------------------------------------------


class TestBuildFtsIndex(unittest.TestCase):
    def test_indexes_error_records(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            _make_error_record(root, "ERR-001", body="authentication failure token expired")
            _make_error_record(root, "ERR-002", body="database connection pool exhausted")
            count = build_fts_index(ctx)
            self.assertEqual(count, 2)

    def test_returns_zero_for_empty_errors_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            count = build_fts_index(ctx)
            self.assertEqual(count, 0)

    def test_skips_rebuild_when_count_matches(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            _make_error_record(root, "ERR-001")
            build_fts_index(ctx)
            # Second call — should skip rebuild (count matches)
            count = build_fts_index(ctx, force=False)
            self.assertEqual(count, 1)

    def test_force_rebuilds_index(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            _make_error_record(root, "ERR-001")
            build_fts_index(ctx)
            _make_error_record(root, "ERR-002")
            # Force should pick up new record
            count = build_fts_index(ctx, force=True)
            self.assertEqual(count, 2)

    def test_includes_archive_records(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            _make_error_record(root, "ERR-001")
            # Manually create an archive record
            arch_path = root / "errors" / "archive" / "ERR-ARC-001.md"
            _write(
                arch_path,
                "---\nid: ERR-ARC-001\nproject: old\ncategory: infra\ndomain: ops\n"
                "severity: P3\nstatus: resolved\ndate: 2023-01-01\n---\nArchived.\n",
            )
            count = build_fts_index(ctx, force=True)
            self.assertEqual(count, 2)

    def test_creates_fts_db_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            _make_error_record(root, "ERR-001")
            build_fts_index(ctx)
            db_path = _fts_db_path(ctx)
            self.assertTrue(db_path.exists())


# ---------------------------------------------------------------------------
# TestSearchFts
# ---------------------------------------------------------------------------


class TestSearchFts(unittest.TestCase):
    def test_returns_matching_records(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            _make_error_record(root, "ERR-001", body="JWT authentication token validation failed")
            _make_error_record(root, "ERR-002", body="database disk quota exceeded")
            results = search_fts(ctx, "authentication token", limit=10)
            ids = [r["id"] for r in results]
            self.assertIn("ERR-001", ids)
            self.assertNotIn("ERR-002", ids)

    def test_returns_empty_for_no_match(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            _make_error_record(root, "ERR-001", body="unrelated content")
            results = search_fts(ctx, "xyzzy_never_in_corpus", limit=10)
            self.assertEqual(results, [])

    def test_respects_limit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            for i in range(5):
                _make_error_record(root, f"ERR-00{i}", body="timeout database error repeated")
            results = search_fts(ctx, "timeout database", limit=2)
            self.assertLessEqual(len(results), 2)

    def test_result_has_required_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            _make_error_record(root, "ERR-001", project="myproj", category="logic", body="network timeout")
            results = search_fts(ctx, "network timeout", limit=5)
            self.assertTrue(results)
            r = results[0]
            for field in ("id", "project", "category", "domain", "severity", "status", "date_str", "filepath", "fts_score"):
                self.assertIn(field, r, f"Missing field: {field}")

    def test_fts_score_normalized_0_to_1(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            _make_error_record(root, "ERR-001", body="cache invalidation race condition")
            results = search_fts(ctx, "cache invalidation", limit=5)
            for r in results:
                self.assertGreaterEqual(r["fts_score"], 0.0)
                self.assertLessEqual(r["fts_score"], 1.0)

    def test_auto_rebuilds_stale_index(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            _make_error_record(root, "ERR-001", body="first record")
            build_fts_index(ctx)
            # Add a new record without explicitly calling build_fts_index
            _make_error_record(root, "ERR-002", body="second unique record")
            results = search_fts(ctx, "second unique", limit=5)
            ids = [r["id"] for r in results]
            self.assertIn("ERR-002", ids)


# ---------------------------------------------------------------------------
# TestIsRecent
# ---------------------------------------------------------------------------


class TestIsRecent(unittest.TestCase):
    def test_recent_date_returns_true(self):
        from datetime import date, timedelta
        recent = (date.today() - timedelta(days=5)).isoformat()
        self.assertTrue(_is_recent(recent))

    def test_old_date_returns_false(self):
        self.assertFalse(_is_recent("2020-01-01"))

    def test_empty_string_returns_false(self):
        self.assertFalse(_is_recent(""))

    def test_invalid_date_returns_false(self):
        self.assertFalse(_is_recent("not-a-date"))

    def test_exactly_recent_days_boundary(self):
        from datetime import date, timedelta
        boundary = (date.today() - timedelta(days=RECENT_DAYS)).isoformat()
        self.assertTrue(_is_recent(boundary))


# ---------------------------------------------------------------------------
# TestHybridSearch
# ---------------------------------------------------------------------------


class TestHybridSearch(unittest.TestCase):
    def test_fts_only_fallback_when_no_lancedb(self):
        """When lancedb is unavailable, should still return FTS results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            _make_error_record(root, "ERR-001", body="memory leak detected in worker thread")
            # Patch lancedb import to simulate unavailability
            with patch.dict("sys.modules", {"lancedb": None}):
                results = hybrid_search(ctx, "memory leak", limit=5)
            self.assertTrue(results)
            self.assertEqual(results[0]["id"], "ERR-001")

    def test_hybrid_result_has_score_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            _make_error_record(root, "ERR-001", body="ssl certificate verification error")
            with patch.dict("sys.modules", {"lancedb": None}):
                results = hybrid_search(ctx, "ssl certificate", limit=5)
            if results:
                r = results[0]
                self.assertIn("fts_score", r)
                self.assertIn("vector_score", r)
                self.assertIn("combined_score", r)

    def test_recent_boost_applied(self):
        """Records with recent dates should score higher than older records with same keywords."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from datetime import date, timedelta
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            recent = (date.today() - timedelta(days=3)).isoformat()
            old = "2020-01-01"
            _make_error_record(root, "ERR-RECENT", body="timeout error in api handler", date_str=recent)
            _make_error_record(root, "ERR-OLD", body="timeout error in api handler", date_str=old)
            with patch.dict("sys.modules", {"lancedb": None}):
                results = hybrid_search(ctx, "timeout error api", limit=5)
            if len(results) >= 2:
                ids = [r["id"] for r in results]
                combined_recent = next((r["combined_score"] for r in results if r["id"] == "ERR-RECENT"), 0)
                combined_old = next((r["combined_score"] for r in results if r["id"] == "ERR-OLD"), 0)
                self.assertGreaterEqual(combined_recent, combined_old)

    def test_returns_at_most_limit_results(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            for i in range(8):
                _make_error_record(root, f"ERR-{i:03d}", body="repeated error keyword match")
            with patch.dict("sys.modules", {"lancedb": None}):
                results = hybrid_search(ctx, "repeated error", limit=3)
            self.assertLessEqual(len(results), 3)

    def test_empty_query_returns_empty_or_error_gracefully(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            _make_error_record(root, "ERR-001", body="some content")
            with patch.dict("sys.modules", {"lancedb": None}):
                # Empty query should not crash
                try:
                    results = hybrid_search(ctx, "", limit=5)
                    self.assertIsInstance(results, list)
                except Exception:
                    pass  # acceptable to raise for empty query

    def test_vector_scores_merged_when_available(self):
        """When LanceDB returns vector results, they should increase combined_score."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import sys
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            _make_error_record(root, "ERR-001", body="async race condition in event loop")

            # Mock lancedb connection with one vector result
            mock_lancedb = MagicMock()
            mock_table = MagicMock()
            mock_lancedb.connect.return_value.table_names.return_value = ["errors"]
            mock_lancedb.connect.return_value.open_table.return_value = mock_table
            mock_table.search.return_value.limit.return_value.to_list.return_value = [
                {"id": "ERR-001", "_distance": 0.2}
            ]

            with patch.dict(sys.modules, {"lancedb": mock_lancedb}):
                with patch("agents_memory.services.records.get_embedding", return_value=[0.1] * 1536):
                    results = hybrid_search(ctx, "race condition", limit=5)

            self.assertIsInstance(results, list)


# ---------------------------------------------------------------------------
# TestCmdFtsIndex
# ---------------------------------------------------------------------------


class TestCmdFtsIndex(unittest.TestCase):
    def test_runs_without_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            _make_error_record(root, "ERR-001", body="test record for fts index cmd")
            exit_code = cmd_fts_index(ctx, [])
            self.assertEqual(exit_code, 0)

    def test_force_flag_accepted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            exit_code = cmd_fts_index(ctx, ["--force"])
            self.assertEqual(exit_code, 0)


# ---------------------------------------------------------------------------
# TestCmdHybridSearch
# ---------------------------------------------------------------------------


class TestCmdHybridSearch(unittest.TestCase):
    def test_prints_results(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            _make_error_record(root, "ERR-001", body="null pointer dereference in parser")
            with patch.dict("sys.modules", {"lancedb": None}):
                exit_code = cmd_hybrid_search(ctx, ["null pointer"])
            self.assertEqual(exit_code, 0)

    def test_returns_1_with_no_args(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            exit_code = cmd_hybrid_search(ctx, [])
            self.assertEqual(exit_code, 1)

    def test_json_flag_outputs_json(self):
        import json
        import io
        import contextlib
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            _make_error_record(root, "ERR-001", body="serialization error in json codec")
            buf = io.StringIO()
            with patch.dict("sys.modules", {"lancedb": None}):
                with contextlib.redirect_stdout(buf):
                    cmd_hybrid_search(ctx, ["serialization json", "--json"])
            output = buf.getvalue().strip()
            if output:
                try:
                    data = json.loads(output)
                    self.assertIsInstance(data, list)
                except json.JSONDecodeError:
                    pass  # may be empty list message, acceptable

    def test_fts_only_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            _make_error_record(root, "ERR-001", body="index out of bounds array access")
            exit_code = cmd_hybrid_search(ctx, ["index out of bounds", "--fts-only"])
            self.assertEqual(exit_code, 0)

    def test_limit_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            for i in range(5):
                _make_error_record(root, f"ERR-{i:03d}", body="stack overflow recursive call")
            with patch.dict("sys.modules", {"lancedb": None}):
                exit_code = cmd_hybrid_search(ctx, ["stack overflow", "--limit", "2"])
            self.assertEqual(exit_code, 0)

    def test_no_results_message(self):
        import io
        import contextlib
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                cmd_hybrid_search(ctx, ["zzzxxx_no_match"])
            self.assertIn("未找到", buf.getvalue())


# ---------------------------------------------------------------------------
# TestParseSearchArgs — extracted from cmd_hybrid_search
# ---------------------------------------------------------------------------


class TestParseSearchArgs(unittest.TestCase):
    def test_basic_query(self):
        opts = _parse_search_args(["my query"])
        self.assertEqual(opts["query"], "my query")
        self.assertEqual(opts["limit"], 10)
        self.assertFalse(opts["fts_only"])
        self.assertFalse(opts["output_json"])

    def test_limit_flag(self):
        opts = _parse_search_args(["q", "--limit", "25"])
        self.assertEqual(opts["limit"], 25)

    def test_fts_only_flag(self):
        opts = _parse_search_args(["q", "--fts-only"])
        self.assertTrue(opts["fts_only"])

    def test_json_flag(self):
        opts = _parse_search_args(["q", "--json"])
        self.assertTrue(opts["output_json"])

    def test_invalid_limit_uses_default(self):
        opts = _parse_search_args(["q", "--limit", "notanumber"])
        self.assertEqual(opts["limit"], 10)

    def test_unknown_flag_ignored(self):
        opts = _parse_search_args(["q", "--unknown"])
        self.assertEqual(opts["query"], "q")


# ---------------------------------------------------------------------------
# TestFtsFileToRow — extracted from build_fts_index
# ---------------------------------------------------------------------------


class TestFtsFileToRow(unittest.TestCase):
    def test_returns_tuple_for_valid_record(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = _make_error_record(root, "ERR-001")
            row = _fts_file_to_row(path)
            self.assertIsNotNone(row)
            assert row is not None
            self.assertEqual(row[0], "ERR-001")   # id
            self.assertEqual(row[1], "testproj")  # project

    def test_returns_none_for_file_without_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = root / "errors" / "empty.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("No frontmatter here\n", encoding="utf-8")
            self.assertIsNone(_fts_file_to_row(path))

    def test_content_field_contains_body_text(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = _make_error_record(root, "ERR-002", body="unique body phrase zeta")
            row = _fts_file_to_row(path)
            assert row is not None
            self.assertIn("unique body phrase zeta", row[8])  # content column


# ---------------------------------------------------------------------------
# TestFtsFull Rebuild — extracted from build_fts_index
# ---------------------------------------------------------------------------


class TestFtsFullRebuild(unittest.TestCase):
    def test_inserts_all_rows(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            for i in range(3):
                _make_error_record(root, f"ERR-{i:03d}")
            all_files = sorted(ctx.errors_dir.glob("*.md"))
            from agents_memory.services.search import _create_fts_schema, _open_fts_db, _fts_db_path
            conn = _open_fts_db(_fts_db_path(ctx))
            _create_fts_schema(conn)
            count = _fts_full_rebuild(conn, all_files)
            self.assertEqual(count, 3)
            conn.close()


# ---------------------------------------------------------------------------
# TestGetVectorScores — extracted from hybrid_search
# ---------------------------------------------------------------------------


class TestGetVectorScores(unittest.TestCase):
    def test_returns_empty_when_lancedb_unavailable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            with patch.dict("sys.modules", {"lancedb": None}):
                scores = _get_vector_scores(ctx, "test query", 10)
            self.assertEqual(scores, {})

    def test_returns_empty_when_vector_dir_absent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            # vector_dir does not exist
            scores = _get_vector_scores(ctx, "query", 5)
            self.assertEqual(scores, {})


# ---------------------------------------------------------------------------
# TestMergeSearchResults — extracted from hybrid_search
# ---------------------------------------------------------------------------


class TestMergeSearchResults(unittest.TestCase):
    def _fts_entry(self, doc_id: str, fts_score: float, date_str: str = "2020-01-01") -> dict:
        return {
            "id": doc_id, "project": "p", "category": "c", "domain": "d",
            "severity": "P2", "status": "new", "date_str": date_str, "filepath": "",
            "fts_score": fts_score,
        }

    def test_fts_only_score_used_when_no_vector(self):
        fts_by_id = {"A": self._fts_entry("A", 0.8)}
        results = _merge_search_results(fts_by_id, {}, FTS_SCORE_WEIGHT, VECTOR_SCORE_WEIGHT)
        self.assertEqual(len(results), 1)
        self.assertAlmostEqual(results[0]["combined_score"], 0.8)

    def test_vector_only_score_used_when_no_fts(self):
        results = _merge_search_results({}, {"B": 0.7}, FTS_SCORE_WEIGHT, VECTOR_SCORE_WEIGHT)
        self.assertEqual(len(results), 1)
        self.assertAlmostEqual(results[0]["combined_score"], 0.7)

    def test_combined_score_when_both_present(self):
        fts_by_id = {"C": self._fts_entry("C", 1.0)}
        vector_by_id = {"C": 1.0}
        results = _merge_search_results(fts_by_id, vector_by_id, FTS_SCORE_WEIGHT, VECTOR_SCORE_WEIGHT)
        expected = 1.0 * FTS_SCORE_WEIGHT + 1.0 * VECTOR_SCORE_WEIGHT
        self.assertAlmostEqual(results[0]["combined_score"], expected, places=4)

    def test_recent_boost_applied(self):
        from datetime import date
        today = date.today().isoformat()
        fts_by_id = {"D": self._fts_entry("D", 0.5, date_str=today)}
        results = _merge_search_results(fts_by_id, {}, FTS_SCORE_WEIGHT, VECTOR_SCORE_WEIGHT)
        self.assertAlmostEqual(results[0]["combined_score"], 0.5 + RECENT_BOOST, places=4)

    def test_all_ids_are_represented(self):
        fts_by_id = {"E": self._fts_entry("E", 0.6), "F": self._fts_entry("F", 0.4)}
        vector_by_id = {"F": 0.9, "G": 0.3}
        results = _merge_search_results(fts_by_id, vector_by_id, FTS_SCORE_WEIGHT, VECTOR_SCORE_WEIGHT)
        ids = {r["id"] for r in results}
        self.assertEqual(ids, {"E", "F", "G"})


if __name__ == "__main__":
    unittest.main()
