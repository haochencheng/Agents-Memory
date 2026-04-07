"""Tests for Phase 1 wiki additions: compile-truth, timeline, links, lint.

Tests are designed to be fully offline — no LLM API calls are made.
The compile tests mock _call_llm via monkeypatching.
"""

from __future__ import annotations

import os
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from agents_memory.runtime import build_context
from agents_memory.services.wiki import (
    _TIMELINE_HEADER,
    _TIMELINE_SEPARATOR,
    append_timeline_entry,
    build_compiled_page,
    cmd_wiki_backlinks,
    cmd_wiki_link,
    cmd_wiki_lint,
    get_wiki_links,
    list_wiki_topics,
    parse_wiki_sections,
    set_wiki_links,
    update_compiled_truth,
    write_wiki_page,
)
from agents_memory.services.wiki_compile import (
    _parse_compile_args,
    build_compile_prompt,
    cmd_wiki_compile,
    compile_wiki_topic,
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
        return build_context(logger_name=f"tests.wiki_compile.{root.name}", reference_file=__file__)
    finally:
        if previous is None:
            os.environ.pop("AGENTS_MEMORY_ROOT", None)
        else:
            os.environ["AGENTS_MEMORY_ROOT"] = previous


_SAMPLE_V2_PAGE = """\
---
topic: finance-safety
created_at: 2026-01-01
updated_at: 2026-01-01
compiled_at: 2026-01-01
confidence: high
sources: [AME-001]
links: []
---

## 结论（Compiled Truth）

> 综合评估：注意精度问题。

## 已知 Pattern

- 使用 Decimal 而非 float

---

## 时间线

- **2026-01-01** | AME-001 — 首次记录精度问题
"""

_SAMPLE_LEGACY_PAGE = """\
---
topic: python-errors
created_at: 2026-01-01
updated_at: 2026-01-01
confidence: medium
sources: []
---

This is a legacy body with no timeline separator.
"""


# ===========================================================================
# parse_wiki_sections
# ===========================================================================


class TestParseWikiSections(unittest.TestCase):
    def test_splits_compiled_truth_and_timeline(self) -> None:
        sections = parse_wiki_sections(_SAMPLE_V2_PAGE)
        self.assertIn("## 结论", sections["compiled_truth"])
        self.assertIn("## 已知 Pattern", sections["compiled_truth"])
        self.assertIn("AME-001", sections["timeline"])
        self.assertNotIn(_TIMELINE_SEPARATOR, sections["compiled_truth"])

    def test_frontmatter_str_contains_fences(self) -> None:
        sections = parse_wiki_sections(_SAMPLE_V2_PAGE)
        self.assertTrue(sections["frontmatter_str"].startswith("---"))
        self.assertIn("topic: finance-safety", sections["frontmatter_str"])

    def test_legacy_page_has_empty_timeline(self) -> None:
        sections = parse_wiki_sections(_SAMPLE_LEGACY_PAGE)
        self.assertEqual(sections["timeline"], "")
        self.assertIn("legacy body", sections["compiled_truth"])

    def test_page_without_frontmatter(self) -> None:
        sections = parse_wiki_sections("Just a plain body.\n")
        self.assertEqual(sections["frontmatter_str"], "")
        self.assertIn("plain body", sections["compiled_truth"])
        self.assertEqual(sections["timeline"], "")

    def test_empty_content(self) -> None:
        sections = parse_wiki_sections("")
        self.assertEqual(sections["frontmatter_str"], "")
        self.assertEqual(sections["compiled_truth"], "")
        self.assertEqual(sections["timeline"], "")

    def test_timeline_header_stripped_from_timeline(self) -> None:
        """The stored timeline should NOT start with '## 时间线'."""
        sections = parse_wiki_sections(_SAMPLE_V2_PAGE)
        self.assertFalse(sections["timeline"].startswith(_TIMELINE_HEADER))


# ===========================================================================
# build_compiled_page
# ===========================================================================


class TestBuildCompiledPage(unittest.TestCase):
    def test_round_trip_with_timeline(self) -> None:
        sections = parse_wiki_sections(_SAMPLE_V2_PAGE)
        rebuilt = build_compiled_page(
            "finance-safety",
            sections["compiled_truth"],
            sections["timeline"],
            existing_frontmatter=sections["frontmatter_str"],
        )
        rebuilt_sections = parse_wiki_sections(rebuilt)
        self.assertEqual(
            sections["compiled_truth"].strip(),
            rebuilt_sections["compiled_truth"].strip(),
        )
        self.assertEqual(
            sections["timeline"].strip(),
            rebuilt_sections["timeline"].strip(),
        )

    def test_round_trip_without_timeline(self) -> None:
        sections = parse_wiki_sections(_SAMPLE_LEGACY_PAGE)
        rebuilt = build_compiled_page(
            "python-errors",
            sections["compiled_truth"],
            "",
            existing_frontmatter=sections["frontmatter_str"],
        )
        self.assertNotIn(_TIMELINE_SEPARATOR + "\n\n" + _TIMELINE_HEADER, rebuilt)
        self.assertIn(sections["compiled_truth"].strip(), rebuilt)

    def test_fresh_page_gets_compiled_frontmatter(self) -> None:
        rebuilt = build_compiled_page("new-topic", "## Body", "")
        self.assertIn("compiled_at:", rebuilt)
        self.assertIn("links:", rebuilt)
        self.assertIn("new-topic", rebuilt)

    def test_updated_at_refreshed_in_existing_frontmatter(self) -> None:
        from datetime import date
        # Extract proper frontmatter (includes both --- fences) from sample page
        sections = parse_wiki_sections(_SAMPLE_V2_PAGE)
        rebuilt = build_compiled_page(
            "finance-safety",
            "body",
            "",
            existing_frontmatter=sections["frontmatter_str"],
        )
        self.assertIn(f"updated_at: {date.today().isoformat()}", rebuilt)


# ===========================================================================
# append_timeline_entry
# ===========================================================================


class TestAppendTimelineEntry(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.wiki_dir = Path(self._tmp.name) / "wiki"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_creates_page_when_absent(self) -> None:
        path = append_timeline_entry(self.wiki_dir, "new-topic", "- **2026-04-07** | entry 1")
        self.assertTrue(path.exists())
        content = path.read_text(encoding="utf-8")
        self.assertIn("entry 1", content)

    def test_entry_prepended_newest_first(self) -> None:
        append_timeline_entry(self.wiki_dir, "test-topic", "- **2026-01-01** | old entry")
        append_timeline_entry(self.wiki_dir, "test-topic", "- **2026-04-07** | new entry")
        content = (self.wiki_dir / "test-topic.md").read_text(encoding="utf-8")
        new_pos = content.index("new entry")
        old_pos = content.index("old entry")
        self.assertLess(new_pos, old_pos, "newest entry should come before older ones")

    def test_existing_compiled_truth_preserved(self) -> None:
        _write(self.wiki_dir / "my-topic.md", _SAMPLE_V2_PAGE)
        append_timeline_entry(self.wiki_dir, "my-topic", "- **2026-04-07** | new event")
        content = (self.wiki_dir / "my-topic.md").read_text(encoding="utf-8")
        self.assertIn("## 结论", content)
        self.assertIn("精度问题", content)
        self.assertIn("new event", content)

    def test_timeline_section_header_present(self) -> None:
        append_timeline_entry(self.wiki_dir, "solo-topic", "- **2026-04-07** | event")
        content = (self.wiki_dir / "solo-topic.md").read_text(encoding="utf-8")
        self.assertIn(_TIMELINE_HEADER, content)
        self.assertIn(_TIMELINE_SEPARATOR, content)


# ===========================================================================
# update_compiled_truth
# ===========================================================================


class TestUpdateCompiledTruth(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.wiki_dir = Path(self._tmp.name) / "wiki"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_creates_page_when_absent(self) -> None:
        path = update_compiled_truth(self.wiki_dir, "new-topic", "## 新结论\n\n> 摘要")
        self.assertTrue(path.exists())
        content = path.read_text(encoding="utf-8")
        self.assertIn("新结论", content)

    def test_timeline_preserved_after_update(self) -> None:
        _write(self.wiki_dir / "finance-safety.md", _SAMPLE_V2_PAGE)
        update_compiled_truth(self.wiki_dir, "finance-safety", "## 更新结论\n\n> 新摘要")
        content = (self.wiki_dir / "finance-safety.md").read_text(encoding="utf-8")
        self.assertIn("AME-001", content, "original timeline entry should be preserved")
        self.assertIn("更新结论", content)
        self.assertNotIn("注意精度问题", content, "old compiled_truth should be replaced")

    def test_compiled_at_refreshed(self) -> None:
        from datetime import date
        _write(self.wiki_dir / "finance-safety.md", _SAMPLE_V2_PAGE)
        update_compiled_truth(self.wiki_dir, "finance-safety", "new body")
        content = (self.wiki_dir / "finance-safety.md").read_text(encoding="utf-8")
        self.assertIn(f"compiled_at: {date.today().isoformat()}", content)


# ===========================================================================
# get_wiki_links / set_wiki_links
# ===========================================================================


class TestWikiLinks(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.wiki_dir = Path(self._tmp.name) / "wiki"
        self.wiki_dir.mkdir(parents=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _make_page(self, topic: str, links_yaml: str = "links: []") -> Path:
        content = (
            f"---\ntopic: {topic}\ncreated_at: 2026-01-01\n"
            f"updated_at: 2026-01-01\n{links_yaml}\n---\n\nbody\n"
        )
        path = self.wiki_dir / f"{topic}.md"
        _write(path, content)
        return path

    def test_get_wiki_links_empty(self) -> None:
        path = self._make_page("page-a")
        links = get_wiki_links(path.read_text(encoding="utf-8"))
        self.assertEqual(links, [])

    def test_get_wiki_links_with_entries(self) -> None:
        links_yaml = (
            "links:\n"
            "  - topic: page-b\n"
            "    context: \"some context\"\n"
            "  - topic: page-c\n"
        )
        path = self._make_page("page-a", links_yaml)
        links = get_wiki_links(path.read_text(encoding="utf-8"))
        self.assertEqual(len(links), 2)
        self.assertEqual(links[0]["topic"], "page-b")
        self.assertEqual(links[0]["context"], "some context")
        self.assertEqual(links[1]["topic"], "page-c")

    def test_set_wiki_links_replaces_existing(self) -> None:
        links_yaml = "links:\n  - topic: old-topic\n    context: \"old\"\n"
        path = self._make_page("page-a", links_yaml)
        new_links = [{"topic": "new-topic", "context": "new context"}]
        set_wiki_links(self.wiki_dir, "page-a", new_links)
        updated = get_wiki_links(path.read_text(encoding="utf-8"))
        self.assertEqual(len(updated), 1)
        self.assertEqual(updated[0]["topic"], "new-topic")
        self.assertEqual(updated[0]["context"], "new context")
        # old-topic should be gone
        self.assertNotEqual(updated[0]["topic"], "old-topic")

    def test_set_wiki_links_body_preserved(self) -> None:
        path = self._make_page("page-a")
        set_wiki_links(self.wiki_dir, "page-a", [{"topic": "page-b"}])
        content = path.read_text(encoding="utf-8")
        self.assertIn("body", content)

    def test_get_wiki_links_no_frontmatter(self) -> None:
        links = get_wiki_links("plain content without frontmatter")
        self.assertEqual(links, [])


# ===========================================================================
# cmd_wiki_link / cmd_wiki_backlinks
# ===========================================================================


class TestWikiLinkCommands(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.ctx = _build_ctx(self.root)
        self.ctx.wiki_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _make_page(self, topic: str) -> None:
        content = f"---\ntopic: {topic}\ncreated_at: 2026-01-01\nupdated_at: 2026-01-01\nlinks: []\n---\n\nbody\n"
        _write(self.ctx.wiki_dir / f"{topic}.md", content)

    def test_wiki_link_creates_link(self) -> None:
        self._make_page("page-a")
        self._make_page("page-b")
        result = cmd_wiki_link(self.ctx, ["page-a", "page-b", "--context", "test ctx"])
        self.assertEqual(result, 0)
        content = (self.ctx.wiki_dir / "page-a.md").read_text(encoding="utf-8")
        links = get_wiki_links(content)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["topic"], "page-b")

    def test_wiki_link_missing_from_page(self) -> None:
        self._make_page("page-b")
        result = cmd_wiki_link(self.ctx, ["nonexistent", "page-b"])
        self.assertEqual(result, 1)

    def test_wiki_link_idempotent_update_context(self) -> None:
        self._make_page("page-a")
        self._make_page("page-b")
        cmd_wiki_link(self.ctx, ["page-a", "page-b", "--context", "old context"])
        cmd_wiki_link(self.ctx, ["page-a", "page-b", "--context", "new context"])
        content = (self.ctx.wiki_dir / "page-a.md").read_text(encoding="utf-8")
        links = get_wiki_links(content)
        self.assertEqual(len(links), 1)
        self.assertIn("new context", links[0].get("context", ""))

    def test_wiki_backlinks_finds_reference(self) -> None:
        self._make_page("page-a")
        self._make_page("page-b")
        cmd_wiki_link(self.ctx, ["page-a", "page-b"])
        from io import StringIO
        from contextlib import redirect_stdout
        buf = StringIO()
        with redirect_stdout(buf):
            result = cmd_wiki_backlinks(self.ctx, ["page-b"])
        self.assertEqual(result, 0)
        output = buf.getvalue()
        self.assertIn("page-a", output)

    def test_wiki_backlinks_no_results(self) -> None:
        self._make_page("page-x")
        from io import StringIO
        from contextlib import redirect_stdout
        buf = StringIO()
        with redirect_stdout(buf):
            result = cmd_wiki_backlinks(self.ctx, ["page-x"])
        self.assertEqual(result, 0)
        self.assertIn("没有", buf.getvalue())

    def test_wiki_link_no_args(self) -> None:
        result = cmd_wiki_link(self.ctx, [])
        self.assertEqual(result, 1)

    def test_wiki_backlinks_no_args(self) -> None:
        result = cmd_wiki_backlinks(self.ctx, [])
        self.assertEqual(result, 1)


# ===========================================================================
# cmd_wiki_lint
# ===========================================================================


class TestWikiLint(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.ctx = _build_ctx(self.root)
        self.ctx.wiki_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _make_v2_page(self, topic: str, compiled_at: str = "2026-04-07", add_link_to: str = "") -> None:
        links_yaml = ""
        if add_link_to:
            links_yaml = f"  - topic: {add_link_to}\n    context: test\n"
        content = (
            f"---\ntopic: {topic}\ncreated_at: 2026-01-01\n"
            f"updated_at: 2026-04-07\ncompiled_at: {compiled_at}\n"
            f"confidence: high\nsources: []\nlinks:\n{links_yaml}---\n\n## Body\n"
        )
        _write(self.ctx.wiki_dir / f"{topic}.md", content)

    def test_lint_detects_orphan(self) -> None:
        self._make_v2_page("topic-a")
        self._make_v2_page("topic-b")  # both orphans
        from io import StringIO
        from contextlib import redirect_stdout
        buf = StringIO()
        with redirect_stdout(buf):
            cmd_wiki_lint(self.ctx, ["--check", "orphans"])
        self.assertIn("orphan", buf.getvalue())

    def test_lint_no_orphan_when_linked(self) -> None:
        self._make_v2_page("topic-a", add_link_to="topic-b")
        self._make_v2_page("topic-b")
        from io import StringIO
        from contextlib import redirect_stdout
        buf = StringIO()
        with redirect_stdout(buf):
            cmd_wiki_lint(self.ctx, ["--check", "orphans"])
        # topic-b is linked from topic-a, so it's not orphan
        # topic-a is still orphan (nothing links to it)
        output = buf.getvalue()
        self.assertNotIn("topic-b", output)

    def test_lint_detects_stale_compiled_truth(self) -> None:
        self._make_v2_page("old-topic", compiled_at="2025-01-01")  # > 30 days ago
        from io import StringIO
        from contextlib import redirect_stdout
        buf = StringIO()
        with redirect_stdout(buf):
            cmd_wiki_lint(self.ctx, ["--check", "stale"])
        self.assertIn("stale", buf.getvalue())
        self.assertIn("old-topic", buf.getvalue())

    def test_lint_no_issues_message(self) -> None:
        self._make_v2_page("linked-a", add_link_to="linked-b")
        self._make_v2_page("linked-b", add_link_to="linked-a")
        from io import StringIO
        from contextlib import redirect_stdout
        buf = StringIO()
        with redirect_stdout(buf):
            result = cmd_wiki_lint(self.ctx, ["--check", "orphans"])
        self.assertEqual(result, 0)
        self.assertIn("✅", buf.getvalue())

    def test_lint_empty_wiki(self) -> None:
        from io import StringIO
        from contextlib import redirect_stdout
        buf = StringIO()
        with redirect_stdout(buf):
            result = cmd_wiki_lint(self.ctx, [])
        self.assertEqual(result, 0)


# ===========================================================================
# build_compile_prompt
# ===========================================================================


class TestBuildCompilePrompt(unittest.TestCase):
    def test_prompt_contains_topic(self) -> None:
        prompt = build_compile_prompt("finance-safety", "current truth", "error summaries")
        self.assertIn("finance-safety", prompt)

    def test_prompt_contains_current_truth(self) -> None:
        prompt = build_compile_prompt("t", "my current truth content", "errors")
        self.assertIn("my current truth content", prompt)

    def test_prompt_empty_truth_placeholder(self) -> None:
        prompt = build_compile_prompt("t", "", "errors")
        self.assertIn("尚无内容", prompt)

    def test_prompt_contains_error_summaries(self) -> None:
        prompt = build_compile_prompt("t", "truth", "AME-001 type-error python")
        self.assertIn("AME-001", prompt)


# ===========================================================================
# _parse_compile_args
# ===========================================================================


class TestParseCompileArgs(unittest.TestCase):
    def test_topic_positional(self) -> None:
        parsed = _parse_compile_args(["finance-safety"])
        self.assertEqual(parsed["topic"], "finance-safety")

    def test_topic_flag(self) -> None:
        parsed = _parse_compile_args(["--topic", "my-topic"])
        self.assertEqual(parsed["topic"], "my-topic")

    def test_dry_run_flag(self) -> None:
        parsed = _parse_compile_args(["topic", "--dry-run"])
        self.assertTrue(parsed["dry_run"])

    def test_recent_n(self) -> None:
        parsed = _parse_compile_args(["topic", "--recent-n", "50"])
        self.assertEqual(parsed["recent_n"], 50)

    def test_provider_and_model(self) -> None:
        parsed = _parse_compile_args(["topic", "--provider", "openai", "--model", "gpt-4o"])
        self.assertEqual(parsed["provider"], "openai")
        self.assertEqual(parsed["model"], "gpt-4o")

    def test_scope(self) -> None:
        parsed = _parse_compile_args(["topic", "--scope", "all"])
        self.assertEqual(parsed["scope"], "all")


# ===========================================================================
# compile_wiki_topic (mocked LLM)
# ===========================================================================


class TestCompileWikiTopic(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.ctx = _build_ctx(self.root)
        self.ctx.wiki_dir.mkdir(parents=True, exist_ok=True)
        self.ctx.errors_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _make_error(self, record_id: str, category: str = "type-error", project: str = "synapse-network") -> None:
        content = (
            f"---\nid: {record_id}\ncategory: {category}\nproject: {project}\n"
            f"date: 2026-04-01\nstatus: new\nseverity: medium\ndomain: python\n"
            f"promoted_to: \"\"\n---\n\nError body for {record_id}.\n"
        )
        _write(self.ctx.errors_dir / f"{record_id}.md", content)

    def test_dry_run_returns_preview_no_file_written(self) -> None:
        self._make_error("AME-001")
        result = compile_wiki_topic(self.ctx, "test-topic", dry_run=True)
        self.assertEqual(result["status"], "dry_run")
        self.assertTrue(result["dry_run"])
        self.assertIsNone(result["path"])
        self.assertFalse((self.ctx.wiki_dir / "test-topic.md").exists())

    def test_no_errors_returns_skipped(self) -> None:
        result = compile_wiki_topic(self.ctx, "empty-topic")
        self.assertEqual(result["status"], "skipped")

    def test_compile_with_mocked_llm_writes_file(self) -> None:
        self._make_error("AME-002", category="finance-safety")
        self._make_error("AME-003", category="finance-safety")

        with patch(
            "agents_memory.services.wiki_compile._call_llm",
            return_value="## 结论\n\n> 合成摘要\n\n## Pattern\n- pattern 1",
        ):
            result = compile_wiki_topic(self.ctx, "finance-safety")

        self.assertEqual(result["status"], "ok")
        self.assertGreater(result["error_count"], 0)
        self.assertIsNotNone(result["path"])
        wiki_path = Path(result["path"])
        self.assertTrue(wiki_path.exists())
        content = wiki_path.read_text(encoding="utf-8")
        self.assertIn("合成摘要", content)

    def test_compile_appends_timeline(self) -> None:
        self._make_error("AME-004")
        with patch(
            "agents_memory.services.wiki_compile._call_llm",
            return_value="## 结论\n\n> summary",
        ):
            result = compile_wiki_topic(self.ctx, "timeline-topic")

        wiki_path = Path(result["path"])
        content = wiki_path.read_text(encoding="utf-8")
        self.assertIn("wiki-compile", content)
        self.assertIn(_TIMELINE_HEADER, content)

    def test_compile_preserves_existing_timeline(self) -> None:
        _write(self.ctx.wiki_dir / "preserved-topic.md", _SAMPLE_V2_PAGE.replace("topic: finance-safety", "topic: preserved-topic"))
        self._make_error("AME-005")
        with patch(
            "agents_memory.services.wiki_compile._call_llm",
            return_value="## 新结论\n\n> 新摘要",
        ):
            result = compile_wiki_topic(self.ctx, "preserved-topic")
        content = Path(result["path"]).read_text(encoding="utf-8")
        self.assertIn("AME-001", content, "old timeline entry should be preserved")
        self.assertIn("新摘要", content)

    def test_cmd_wiki_compile_dry_run_exit_0(self) -> None:
        self._make_error("AME-006")
        result = cmd_wiki_compile(self.ctx, ["any-topic", "--dry-run"])
        self.assertEqual(result, 0)

    def test_cmd_wiki_compile_no_args_exit_1(self) -> None:
        result = cmd_wiki_compile(self.ctx, [])
        self.assertEqual(result, 1)

    def test_cmd_wiki_compile_with_mock_llm(self) -> None:
        self._make_error("AME-007")
        with patch(
            "agents_memory.services.wiki_compile._call_llm",
            return_value="## 结论\n\n> 摘要",
        ):
            result = cmd_wiki_compile(self.ctx, ["mock-topic"])
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
