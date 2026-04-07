"""Tests for Phase 4 structured ingest pipeline.

All tests are fully offline — no LLM API calls are made.
_call_llm is monkeypatched to return fixture JSON.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents_memory.runtime import build_context
from agents_memory.services.ingest import (
    INGEST_LOG_NAME,
    INGEST_TYPES,
    IngestResult,
    _append_ingest_log,
    _apply_wiki_updates,
    _build_log_entry,
    _ingest_log_path,
    _parse_ingest_args,
    _parse_llm_json,
    _print_ingest_result,
    _run_ingest_llm,
    build_ingest_prompt,
    cmd_ingest,
    ingest_document,
    read_ingest_log,
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
        return build_context(logger_name=f"tests.ingest.{root.name}", reference_file=__file__)
    finally:
        if previous is None:
            os.environ.pop("AGENTS_MEMORY_ROOT", None)


def _make_wiki_page(root: Path, topic: str, body: str = "# Test\nBody text.") -> None:
    _write(root / "memory" / "wiki" / f"{topic}.md", body)


def _make_source_file(root: Path, name: str, content: str) -> Path:
    path = root / "tmp" / name
    _write(path, content)
    return path


def _mock_llm_response(summary: str, topics: list[str], entry: str, update: str = "") -> str:
    """Build a JSON string that mimics the LLM response."""
    return json.dumps({
        "summary": summary,
        "topics": topics,
        "timeline_entry": entry,
        "compiled_truth_update": update,
    }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# TestParseLlmJson
# ---------------------------------------------------------------------------


class TestParseLlmJson(unittest.TestCase):
    def test_parses_valid_json(self):
        raw = '{"summary": "测试", "topics": ["python"], "timeline_entry": "v1.0 released"}'
        result = _parse_llm_json(raw)
        self.assertEqual(result["summary"], "测试")
        self.assertEqual(result["topics"], ["python"])

    def test_strips_markdown_fences(self):
        raw = '```json\n{"summary": "ok", "topics": []}\n```'
        result = _parse_llm_json(raw)
        self.assertEqual(result["summary"], "ok")

    def test_returns_empty_dict_on_invalid_json(self):
        result = _parse_llm_json("not valid json at all")
        self.assertEqual(result, {})

    def test_handles_empty_string(self):
        result = _parse_llm_json("")
        self.assertEqual(result, {})

    def test_handles_json_with_unicode(self):
        raw = json.dumps({"summary": "数据库连接失败", "topics": ["数据库"]})
        result = _parse_llm_json(raw)
        self.assertEqual(result["summary"], "数据库连接失败")

    def test_strips_triple_backtick_without_lang(self):
        raw = "```\n{\"summary\": \"plain fence\", \"topics\": []}\n```"
        result = _parse_llm_json(raw)
        self.assertEqual(result.get("summary"), "plain fence")


# ---------------------------------------------------------------------------
# TestBuildIngestPrompt
# ---------------------------------------------------------------------------


class TestBuildIngestPrompt(unittest.TestCase):
    def test_returns_tuple_of_two_strings(self):
        result = build_ingest_prompt("meeting", "/tmp/notes.md", "content", "proj", ["python", "backend"])
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        system, user = result
        self.assertIsInstance(system, str)
        self.assertIsInstance(user, str)

    def test_system_contains_ingest_type(self):
        system, _ = build_ingest_prompt("decision", "/tmp/adr.md", "body", "", [])
        self.assertIn("decision", system)

    def test_user_contains_known_topics(self):
        _, user = build_ingest_prompt("pr-review", "/tmp/pr.md", "body", "myproj", ["auth", "db"])
        self.assertIn("auth", user)
        self.assertIn("db", user)

    def test_user_truncates_long_content(self):
        long_content = "x" * 10000
        _, user = build_ingest_prompt("meeting", "/path", long_content, "", [])
        self.assertLessEqual(len(user), 8000)  # must be bounded

    def test_empty_topics_shows_none(self):
        _, user = build_ingest_prompt("code-review", "/path", "body", "", [])
        self.assertIn("(none)", user)

    def test_project_included_in_user_prompt(self):
        _, user = build_ingest_prompt("meeting", "/path", "body", "backend-team", [])
        self.assertIn("backend-team", user)


# ---------------------------------------------------------------------------
# TestBuildLogEntry
# ---------------------------------------------------------------------------


class TestBuildLogEntry(unittest.TestCase):
    def test_returns_dict_with_required_keys(self):
        entry = _build_log_entry(
            ingest_type="pr-review",
            source_path="/tmp/pr.md",
            project="myproj",
            summary="Summary text",
            topics=["python"],
            provider="anthropic",
            model="claude-sonnet-4-5",
        )
        required = {"timestamp", "ingest_type", "source_path", "project", "summary", "topics", "provider", "model"}
        self.assertEqual(required, set(entry.keys()))

    def test_timestamp_ends_with_z(self):
        entry = _build_log_entry(
            ingest_type="meeting", source_path="", project="", summary="",
            topics=[], provider="openai", model="gpt-4o-mini"
        )
        self.assertTrue(entry["timestamp"].endswith("Z"))

    def test_all_types_can_build_log_entry(self):
        for t in INGEST_TYPES:
            entry = _build_log_entry(
                ingest_type=t, source_path="/f", project="p", summary="s",
                topics=[], provider="anthropic", model="m"
            )
            self.assertEqual(entry["ingest_type"], t)


# ---------------------------------------------------------------------------
# TestIngestLog
# ---------------------------------------------------------------------------


class TestIngestLog(unittest.TestCase):
    def test_append_and_read_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            entry = _build_log_entry(
                ingest_type="meeting", source_path="/tmp/m.md", project="p",
                summary="Test", topics=["topic1"], provider="anthropic", model="m"
            )
            _append_ingest_log(ctx, entry)
            entries = read_ingest_log(ctx)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["ingest_type"], "meeting")

    def test_read_empty_log_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            self.assertEqual(read_ingest_log(ctx), [])

    def test_multiple_entries_appended(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            for i in range(3):
                entry = _build_log_entry(
                    ingest_type="decision", source_path=f"/tmp/d{i}.md", project="",
                    summary=f"Decision {i}", topics=[], provider="openai", model="gpt"
                )
                _append_ingest_log(ctx, entry)
            entries = read_ingest_log(ctx)
            self.assertEqual(len(entries), 3)

    def test_log_path_is_in_memory_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            path = _ingest_log_path(ctx)
            self.assertEqual(path.parent, ctx.memory_dir)
            self.assertEqual(path.name, INGEST_LOG_NAME)

    def test_corrupt_line_skipped(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            log_path = _ingest_log_path(ctx)
            good_entry = json.dumps({"ingest_type": "meeting", "timestamp": "2024-01-01T00:00:00Z"})
            _write(log_path, f"{good_entry}\nNOT JSON\n{good_entry}\n")
            entries = read_ingest_log(ctx)
            self.assertEqual(len(entries), 2)


# ---------------------------------------------------------------------------
# TestIngestDocument
# ---------------------------------------------------------------------------


class TestIngestDocument(unittest.TestCase):
    def test_dry_run_does_not_modify_wiki(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            _make_wiki_page(root, "python")
            src = _make_source_file(root, "pr.md", "## PR Description\nFix auth bug")
            mock_response = _mock_llm_response(
                summary="修复认证问题",
                topics=["python"],
                entry="2024-01-15 [pr-review] 修复了 OAuth token 验证失败问题",
            )
            with patch("agents_memory.services.ingest._call_llm", return_value=mock_response):
                result = ingest_document(ctx, str(src), "pr-review", dry_run=True)
            self.assertTrue(result.dry_run)
            # Log should NOT be written in dry_run
            log_path = _ingest_log_path(ctx)
            self.assertFalse(log_path.exists())

    def test_raises_for_invalid_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            src = _make_source_file(root, "src.md", "content")
            with self.assertRaises(ValueError):
                ingest_document(ctx, str(src), "invalid-type")

    def test_returns_error_for_missing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            result = ingest_document(ctx, "/nonexistent/path/file.md", "meeting")
            self.assertNotEqual(result.error, "")

    def test_updates_wiki_timeline_on_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            _make_wiki_page(root, "python", "---\ntopic: python\n---\n# Python\nBody.\n")
            src = _make_source_file(root, "meeting.md", "# Meeting Notes\nDiscussed Python logging")
            mock_response = _mock_llm_response(
                summary="讨论了 Python logging 模块使用方式",
                topics=["python"],
                entry="2024-01-15 [meeting] 确认 Python logging 最佳实践",
            )
            with patch("agents_memory.services.ingest._call_llm", return_value=mock_response):
                result = ingest_document(ctx, str(src), "meeting", dry_run=False)
            # Check timeline was appended
            wiki_path = root / "memory" / "wiki" / "python.md"
            content = wiki_path.read_text(encoding="utf-8")
            self.assertIn("meeting", content)

    def test_writes_ingest_log_on_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            _make_wiki_page(root, "backend")
            src = _make_source_file(root, "decision.md", "# Decision\nUse PostgreSQL")
            mock_response = _mock_llm_response(
                summary="决定使用 PostgreSQL 作为主数据库",
                topics=["backend"],
                entry="2024-01-20 [decision] 确认数据库选型",
            )
            with patch("agents_memory.services.ingest._call_llm", return_value=mock_response):
                ingest_document(ctx, str(src), "decision", project="infra")
            entries = read_ingest_log(ctx)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["ingest_type"], "decision")
            self.assertEqual(entries[0]["project"], "infra")

    def test_unknown_topics_not_updated(self):
        """Topics returned by LLM that don't exist in wiki should be ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            # No wiki pages exist
            src = _make_source_file(root, "pr.md", "PR content")
            mock_response = _mock_llm_response(
                summary="PR summary",
                topics=["nonexistent-topic"],
                entry="2024-01-20 [pr-review] Some entry",
            )
            with patch("agents_memory.services.ingest._call_llm", return_value=mock_response):
                result = ingest_document(ctx, str(src), "pr-review")
            self.assertEqual(result.topics_updated, [])
            self.assertEqual(result.timeline_entries_added, 0)

    def test_all_ingest_types_accepted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            src = _make_source_file(root, "doc.md", "Document content")
            for ingest_type in INGEST_TYPES:
                mock_response = _mock_llm_response(
                    summary=f"{ingest_type} summary",
                    topics=[],
                    entry=f"Entry for {ingest_type}",
                )
                with patch("agents_memory.services.ingest._call_llm", return_value=mock_response):
                    result = ingest_document(ctx, str(src), ingest_type, dry_run=True)
                self.assertEqual(result.ingest_type, ingest_type)
                self.assertEqual(result.error, "")

    def test_result_fields_populated(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            src = _make_source_file(root, "doc.md", "PR content here")
            mock_response = _mock_llm_response(
                summary="PR reviewed and merged",
                topics=[],
                entry="2024-01-10 [pr-review] Merged feature branch",
            )
            with patch("agents_memory.services.ingest._call_llm", return_value=mock_response):
                result = ingest_document(ctx, str(src), "pr-review", project="myproj", dry_run=True)
            self.assertEqual(result.ingest_type, "pr-review")
            self.assertEqual(result.project, "myproj")
            self.assertEqual(result.summary, "PR reviewed and merged")
            self.assertIsInstance(result.topics_updated, list)
            self.assertIsInstance(result.log_entry, dict)


# ---------------------------------------------------------------------------
# TestCmdIngest
# ---------------------------------------------------------------------------


class TestCmdIngest(unittest.TestCase):
    def test_returns_1_with_no_args(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            self.assertEqual(cmd_ingest(ctx, []), 1)

    def test_returns_1_with_missing_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            src = _make_source_file(root, "f.md", "content")
            self.assertEqual(cmd_ingest(ctx, [str(src)]), 1)

    def test_returns_1_with_invalid_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            src = _make_source_file(root, "f.md", "content")
            self.assertEqual(cmd_ingest(ctx, [str(src), "--type", "bogus-type"]), 1)

    def test_dry_run_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            src = _make_source_file(root, "pr.md", "PR description")
            mock_response = _mock_llm_response("summary", [], "entry")
            with patch("agents_memory.services.ingest._call_llm", return_value=mock_response):
                exit_code = cmd_ingest(ctx, [str(src), "--type", "pr-review", "--dry-run"])
            self.assertEqual(exit_code, 0)

    def test_log_flag_shows_log(self):
        import io
        import contextlib
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            # Empty log
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                cmd_ingest(ctx, ["dummy", "--log"])
            self.assertIn("空", buf.getvalue())

    def test_project_flag_accepted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            src = _make_source_file(root, "m.md", "Meeting notes")
            mock_response = _mock_llm_response("summary", [], "entry")
            with patch("agents_memory.services.ingest._call_llm", return_value=mock_response):
                exit_code = cmd_ingest(ctx, [str(src), "--type", "meeting", "--project", "team-alpha"])
            self.assertEqual(exit_code, 0)


# ---------------------------------------------------------------------------
# TestParseIngestArgs — new helper extracted from cmd_ingest
# ---------------------------------------------------------------------------


class TestParseIngestArgs(unittest.TestCase):
    def test_basic_type_flag(self):
        opts = _parse_ingest_args(["file.md", "--type", "meeting"])
        self.assertEqual(opts["source_path"], "file.md")
        self.assertEqual(opts["ingest_type"], "meeting")
        self.assertFalse(opts["dry_run"])
        self.assertFalse(opts["show_log"])

    def test_dry_run_flag(self):
        opts = _parse_ingest_args(["file.md", "--type", "meeting", "--dry-run"])
        self.assertTrue(opts["dry_run"])

    def test_log_flag(self):
        opts = _parse_ingest_args(["dummy", "--log"])
        self.assertTrue(opts["show_log"])

    def test_project_flag(self):
        opts = _parse_ingest_args(["f.md", "--type", "decision", "--project", "test-proj"])
        self.assertEqual(opts["project"], "test-proj")

    def test_provider_and_model_flags(self):
        opts = _parse_ingest_args(["f.md", "--type", "pr-review", "--provider", "openai", "--model", "gpt-4o"])
        self.assertEqual(opts["provider"], "openai")
        self.assertEqual(opts["model"], "gpt-4o")

    def test_unknown_flag_ignored(self):
        # Should not raise — unknown flags are silently skipped
        opts = _parse_ingest_args(["f.md", "--type", "meeting", "--unknown-flag"])
        self.assertEqual(opts["ingest_type"], "meeting")


# ---------------------------------------------------------------------------
# TestApplyWikiUpdates — extracted from ingest_document
# ---------------------------------------------------------------------------


class TestApplyWikiUpdates(unittest.TestCase):
    def test_empty_topics_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            updated, count = _apply_wiki_updates(ctx, [], "meeting", "entry", "update")
            self.assertEqual(updated, [])
            self.assertEqual(count, 0)

    def test_appends_timeline_when_entry_given(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            _make_wiki_page(root, "mytopic")
            _apply_wiki_updates(ctx, ["mytopic"], "meeting", "timeline entry text", "")
            page = (ctx.wiki_dir / "mytopic.md").read_text(encoding="utf-8")
            self.assertIn("timeline entry text", page)

    def test_no_timeline_when_entry_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            _make_wiki_page(root, "mytopic2")
            _, count = _apply_wiki_updates(ctx, ["mytopic2"], "meeting", "", "")
            self.assertEqual(count, 0)

    def test_compiled_truth_updated_for_first_topic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            _make_wiki_page(root, "alpha")
            updated, _ = _apply_wiki_updates(ctx, ["alpha"], "decision", "entry", "new compiled truth value")
            self.assertIn("alpha", updated)
            page = (ctx.wiki_dir / "alpha.md").read_text(encoding="utf-8")
            self.assertIn("new compiled truth value", page)


# ---------------------------------------------------------------------------
# TestRunIngestLlm — extracted LLM call helper
# ---------------------------------------------------------------------------


class TestRunIngestLlm(unittest.TestCase):
    def test_returns_parsed_dict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src = _make_source_file(root, "doc.md", "# PR\nSome change.")
            mock_resp = _mock_llm_response("test summary", [], "timeline entry")
            with patch("agents_memory.services.ingest._call_llm", return_value=mock_resp):
                result = _run_ingest_llm(str(src), "pr-review", "proj", "anthropic", "claude-3-5-haiku", [])
            self.assertEqual(result["summary"], "test summary")

    def test_raises_oserror_for_missing_file(self):
        with self.assertRaises(OSError):
            _run_ingest_llm("/nonexistent/file.md", "meeting", "", "anthropic", "model", [])


# ---------------------------------------------------------------------------
# TestPrintIngestResult — output helper
# ---------------------------------------------------------------------------


class TestPrintIngestResult(unittest.TestCase):
    def test_dry_run_prefix(self):
        import io, contextlib
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            r = IngestResult(
                ingest_type="meeting", source_path="f.md", project="p",
                summary="summary text", dry_run=True,
            )
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                _print_ingest_result(r, True, ctx)
            self.assertIn("DRY-RUN", buf.getvalue())
            self.assertIn("summary text", buf.getvalue())

    def test_success_prefix(self):
        import io, contextlib
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_ctx(root)
            r = IngestResult(
                ingest_type="meeting", source_path="f.md", project="proj",
                summary="completed summary", dry_run=False,
            )
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                _print_ingest_result(r, False, ctx)
            self.assertIn("✅", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
