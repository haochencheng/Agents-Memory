from __future__ import annotations

import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from agents_memory.runtime import build_context
from agents_memory.services.wiki import (
    _excerpt_around,
    _frontmatter_end,
    _parse_limit_arg,
    _parse_topic_arg,
    _refresh_updated_at,
    _resolve_content_input,
    cmd_wiki_ingest,
    cmd_wiki_list,
    cmd_wiki_query,
    cmd_wiki_sync,
    ingest_file,
    list_wiki_topics,
    read_wiki_page,
    search_wiki,
    write_wiki_page,
)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_context(root: Path):
    _write_text(root / "templates" / "index.example.md", "index\n")
    _write_text(root / "templates" / "projects.example.md", "# Projects\n")
    _write_text(root / "templates" / "rules.example.md", "# Rules\n")
    previous = os.environ.get("AGENTS_MEMORY_ROOT")
    os.environ["AGENTS_MEMORY_ROOT"] = str(root)
    try:
        return build_context(logger_name=f"tests.wiki.{root.name}", reference_file=__file__)
    finally:
        if previous is None:
            os.environ.pop("AGENTS_MEMORY_ROOT", None)
        else:
            os.environ["AGENTS_MEMORY_ROOT"] = previous


class WikiArgParserTests(unittest.TestCase):
    def test_parse_limit_arg_extracts_limit(self) -> None:
        limit, remaining = _parse_limit_arg(["--limit", "10", "extra"])
        self.assertEqual(limit, 10)
        self.assertEqual(remaining, ["extra"])

    def test_parse_limit_arg_uses_default_when_absent(self) -> None:
        limit, remaining = _parse_limit_arg(["query"])
        self.assertEqual(limit, 5)
        self.assertEqual(remaining, ["query"])

    def test_parse_topic_arg_extracts_topic(self) -> None:
        topic, remaining = _parse_topic_arg(["--topic", "my-topic", "extra"])
        self.assertEqual(topic, "my-topic")
        self.assertEqual(remaining, ["extra"])

    def test_parse_topic_arg_returns_none_when_absent(self) -> None:
        topic, remaining = _parse_topic_arg(["extra"])
        self.assertIsNone(topic)
        self.assertEqual(remaining, ["extra"])

    def test_resolve_content_input_from_content_flag(self) -> None:
        content, _, err = _resolve_content_input(["--content", "hello world"])
        self.assertEqual(content, "hello world")
        self.assertIsNone(err)

    def test_resolve_content_input_from_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            f = Path(tmpdir) / "c.md"
            f.write_text("file content\n", encoding="utf-8")
            content, _, err = _resolve_content_input(["--from-file", str(f)])
            self.assertEqual(content, "file content\n")
            self.assertIsNone(err)

    def test_resolve_content_input_error_on_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            content, _, err = _resolve_content_input(["--from-file", str(Path(tmpdir) / "nope.md")])
            self.assertIsNone(content)
            self.assertEqual(err, 1)


class WikiHelpersTests(unittest.TestCase):
    def test_frontmatter_end_returns_offset_after_closing_fence(self) -> None:
        content = "---\ntopic: foo\n---\n\nbody"
        pos = _frontmatter_end(content)
        self.assertEqual(content[pos:], "\nbody")

    def test_frontmatter_end_returns_zero_when_no_frontmatter(self) -> None:
        self.assertEqual(_frontmatter_end("just body"), 0)

    def test_refresh_updated_at_replaces_value(self) -> None:
        content = "---\ntopic: t\nupdated_at: 2020-01-01\n---\n"
        result = _refresh_updated_at(content, "2026-04-06")
        self.assertIn("updated_at: 2026-04-06", result)
        self.assertNotIn("2020-01-01", result)

    def test_excerpt_around_returns_surrounding_lines(self) -> None:
        content = "line1\nline2\ntarget keyword here\nline4\nline5"
        excerpt = _excerpt_around(content, "keyword")
        self.assertIn("target keyword here", excerpt)

    def test_excerpt_around_falls_back_to_first_lines(self) -> None:
        content = "alpha\nbeta\ngamma"
        excerpt = _excerpt_around(content, "zzz")
        self.assertIn("alpha", excerpt)


class WikiPageTests(unittest.TestCase):
    def test_list_topics_empty_when_dir_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki_dir = Path(tmpdir) / "wiki"
            self.assertEqual(list_wiki_topics(wiki_dir), [])

    def test_list_topics_returns_sorted_stems(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki_dir = Path(tmpdir) / "wiki"
            wiki_dir.mkdir()
            (wiki_dir / "python.md").write_text("# python\n", encoding="utf-8")
            (wiki_dir / "errors.md").write_text("# errors\n", encoding="utf-8")
            self.assertEqual(list_wiki_topics(wiki_dir), ["errors", "python"])

    def test_read_wiki_page_returns_none_for_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki_dir = Path(tmpdir) / "wiki"
            self.assertIsNone(read_wiki_page(wiki_dir, "nonexistent"))

    def test_write_and_read_wiki_page_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki_dir = Path(tmpdir) / "wiki"
            write_wiki_page(wiki_dir, "python", "## Rules\n- Use type hints\n")
            content = read_wiki_page(wiki_dir, "python")
            self.assertIsNotNone(content)
            assert content is not None
            self.assertIn("Use type hints", content)
            self.assertIn("topic: python", content)

    def test_write_wiki_page_creates_frontmatter_when_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki_dir = Path(tmpdir) / "wiki"
            path = write_wiki_page(wiki_dir, "docs", "body text", source="README.md")
            content = path.read_text(encoding="utf-8")
            self.assertIn("topic: docs", content)
            self.assertIn("sources: [README.md]", content)
            self.assertIn("body text", content)

    def test_write_wiki_page_preserves_frontmatter_on_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki_dir = Path(tmpdir) / "wiki"
            write_wiki_page(wiki_dir, "python", "initial body")
            write_wiki_page(wiki_dir, "python", "updated body")
            content = read_wiki_page(wiki_dir, "python")
            assert content is not None
            self.assertIn("topic: python", content)
            self.assertIn("updated body", content)
            self.assertNotIn("initial body", content)

    def test_write_wiki_page_accepts_full_content_with_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki_dir = Path(tmpdir) / "wiki"
            full = "---\ntopic: custom\ncreated_at: 2020-01-01\nupdated_at: 2020-01-01\nconfidence: high\nsources: []\n---\n\ncustom body\n"
            path = write_wiki_page(wiki_dir, "custom", full)
            content = path.read_text(encoding="utf-8")
            self.assertIn("confidence: high", content)
            self.assertIn("custom body", content)

    def test_write_wiki_page_refreshes_updated_at_in_full_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki_dir = Path(tmpdir) / "wiki"
            full = "---\ntopic: t\ncreated_at: 2020-01-01\nupdated_at: 2020-01-01\n---\nbody\n"
            path = write_wiki_page(wiki_dir, "t", full)
            content = path.read_text(encoding="utf-8")
            self.assertNotIn("updated_at: 2020-01-01", content)


class WikiSearchTests(unittest.TestCase):
    def test_search_returns_empty_when_dir_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki_dir = Path(tmpdir) / "wiki"
            self.assertEqual(search_wiki(wiki_dir, "anything"), [])

    def test_search_returns_matching_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki_dir = Path(tmpdir) / "wiki"
            write_wiki_page(wiki_dir, "python", "## Rules\nUse type annotations")
            write_wiki_page(wiki_dir, "frontend", "## Rules\nUse React hooks")
            matches = search_wiki(wiki_dir, "type annotations")
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["topic"], "python")
            self.assertIn("type annotations", matches[0]["excerpt"].lower())

    def test_search_is_case_insensitive(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki_dir = Path(tmpdir) / "wiki"
            write_wiki_page(wiki_dir, "errors", "## Error Patterns\nImportError is common")
            matches = search_wiki(wiki_dir, "IMPORTERROR")
            self.assertEqual(len(matches), 1)

    def test_search_respects_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki_dir = Path(tmpdir) / "wiki"
            for i in range(5):
                write_wiki_page(wiki_dir, f"topic{i}", "shared keyword here")
            matches = search_wiki(wiki_dir, "keyword", limit=2)
            self.assertLessEqual(len(matches), 2)

    def test_search_returns_no_matches_when_query_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki_dir = Path(tmpdir) / "wiki"
            write_wiki_page(wiki_dir, "python", "Python rules")
            matches = search_wiki(wiki_dir, "zzz-not-present")
            self.assertEqual(matches, [])


class WikiIngestTests(unittest.TestCase):
    def test_ingest_file_creates_wiki_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki_dir = Path(tmpdir) / "wiki"
            source = Path(tmpdir) / "my-doc.md"
            source.write_text("# My Doc\nsome content\n", encoding="utf-8")
            path = ingest_file(wiki_dir, source)
            self.assertTrue(path.exists())
            content = path.read_text(encoding="utf-8")
            self.assertIn("# My Doc", content)
            self.assertIn("sources: [my-doc.md]", content)

    def test_ingest_file_uses_explicit_topic(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki_dir = Path(tmpdir) / "wiki"
            source = Path(tmpdir) / "random-name.md"
            source.write_text("content\n", encoding="utf-8")
            path = ingest_file(wiki_dir, source, topic="my-topic")
            self.assertEqual(path.stem, "my-topic")

    def test_ingest_file_raises_for_missing_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki_dir = Path(tmpdir) / "wiki"
            with self.assertRaises(FileNotFoundError):
                ingest_file(wiki_dir, Path(tmpdir) / "does-not-exist.md")

    def test_ingest_normalises_topic_to_lowercase_hyphens(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki_dir = Path(tmpdir) / "wiki"
            source = Path(tmpdir) / "My Topic Name.md"
            source.write_text("content\n", encoding="utf-8")
            path = ingest_file(wiki_dir, source)
            self.assertEqual(path.stem, "my-topic-name")


class WikiCLITests(unittest.TestCase):
    def test_cmd_wiki_list_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_context(root)
            buf = StringIO()
            with redirect_stdout(buf):
                code = cmd_wiki_list(ctx, [])
            self.assertEqual(code, 0)
            self.assertIn("wiki-ingest", buf.getvalue())

    def test_cmd_wiki_list_shows_topics(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_context(root)
            write_wiki_page(ctx.wiki_dir, "python", "content")
            buf = StringIO()
            with redirect_stdout(buf):
                code = cmd_wiki_list(ctx, [])
            self.assertEqual(code, 0)
            self.assertIn("python", buf.getvalue())

    def test_cmd_wiki_query_no_args_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_context(root)
            code = cmd_wiki_query(ctx, [])
            self.assertEqual(code, 1)

    def test_cmd_wiki_query_with_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_context(root)
            write_wiki_page(ctx.wiki_dir, "python", "Always use type hints in Python")
            buf = StringIO()
            with redirect_stdout(buf):
                code = cmd_wiki_query(ctx, ["type hints"])
            self.assertEqual(code, 0)
            self.assertIn("python", buf.getvalue())

    def test_cmd_wiki_query_no_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_context(root)
            buf = StringIO()
            with redirect_stdout(buf):
                code = cmd_wiki_query(ctx, ["zzz-not-present"])
            self.assertEqual(code, 0)
            self.assertIn("未找到", buf.getvalue())

    def test_cmd_wiki_ingest_no_args_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_context(root)
            code = cmd_wiki_ingest(ctx, [])
            self.assertEqual(code, 1)

    def test_cmd_wiki_ingest_creates_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_context(root)
            source = root / "rules-doc.md"
            source.write_text("# Rules\nalways test your code\n", encoding="utf-8")
            buf = StringIO()
            with redirect_stdout(buf):
                code = cmd_wiki_ingest(ctx, [str(source)])
            self.assertEqual(code, 0)
            self.assertIn("✅", buf.getvalue())
            self.assertIsNotNone(read_wiki_page(ctx.wiki_dir, "rules-doc"))

    def test_cmd_wiki_ingest_missing_file_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_context(root)
            buf = StringIO()
            with redirect_stdout(buf):
                code = cmd_wiki_ingest(ctx, [str(root / "missing.md")])
            self.assertEqual(code, 1)

    def test_cmd_wiki_sync_no_args_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_context(root)
            code = cmd_wiki_sync(ctx, [])
            self.assertEqual(code, 1)

    def test_cmd_wiki_sync_with_content_creates_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_context(root)
            buf = StringIO()
            with redirect_stdout(buf):
                code = cmd_wiki_sync(ctx, ["errors", "--content", "Always check for None"])
            self.assertEqual(code, 0)
            content = read_wiki_page(ctx.wiki_dir, "errors")
            self.assertIsNotNone(content)
            assert content is not None
            self.assertIn("Always check for None", content)

    def test_cmd_wiki_sync_from_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_context(root)
            content_file = root / "content.md"
            content_file.write_text("Learned: always validate inputs\n", encoding="utf-8")
            buf = StringIO()
            with redirect_stdout(buf):
                code = cmd_wiki_sync(ctx, ["validation", "--from-file", str(content_file)])
            self.assertEqual(code, 0)
            page = read_wiki_page(ctx.wiki_dir, "validation")
            assert page is not None
            self.assertIn("validate inputs", page)

    def test_cmd_wiki_sync_missing_from_file_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = _build_context(root)
            code = cmd_wiki_sync(ctx, ["topic", "--from-file", str(root / "ghost.md")])
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
