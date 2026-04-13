"""Tests for agents_memory/web — FastAPI endpoints and renderer.

All tests are offline — no real services, no network calls.
Uses FastAPI TestClient (httpx-based) with tmp_path fixtures.

Run:
    pytest tests/test_web_api.py -v
    pytest tests/test_web_api.py -v -k TestPhase1
"""

from __future__ import annotations

import json
import os
import textwrap
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_env(root: Path) -> None:
    """Create minimal project layout in *root* for tests."""
    # Templates (required by build_context bootstrap)
    _write(root / "templates" / "index.example.md", "# Index\n")
    _write(root / "templates" / "projects.example.md", "# Projects\n")
    _write(root / "templates" / "rules.example.md", "# Rules\n")

    # Wiki pages
    _write(
        root / "memory" / "wiki" / "auth-design.md",
        textwrap.dedent("""\
            ---
            topic: auth-design
            updated_at: 2026-03-01
            tags: [auth, jwt]
            links:
              - topic: synapse-architecture
                context: "认证设计依赖系统总体架构"
            ---

            # Auth Design

            JWT access tokens expire after 1 hour.
            Refresh tokens are stored in HttpOnly cookies.
        """),
    )
    _write(
        root / "memory" / "wiki" / "synapse-architecture.md",
        textwrap.dedent("""\
            ---
            topic: synapse-architecture
            updated_at: 2026-04-01
            tags: [backend, design, billing]
            project: synapse-network
            source_path: docs/architecture/overview.md
            ---

            # Synapse Architecture

            Microservices communicate via gRPC.
        """),
    )
    _write(
        root / "memory" / "wiki" / "billing-recharge.md",
        textwrap.dedent("""\
            ---
            topic: billing-recharge
            updated_at: 2026-04-08
            tags: [billing, recharge]
            project: synapse-network
            source_path: docs/billing/recharge.md
            ---

            # Billing Recharge

            用户完成充值后，系统会写入充值成功事件，并更新账户余额。
        """),
    )

    # Error records
    _write(
        root / "errors" / "ERR-2026-0312-001.md",
        textwrap.dedent("""\
            ---
            id: ERR-2026-0312-001
            title: Token validation fails on refresh
            status: open
            project: synapse-network
            severity: high
            date: 2026-03-12
            category: auth
            domain: backend
            ---

            ## Problem
            Refresh token silently rejected after Redis flush.
        """),
    )

    # Rules file
    _write(
        root / "memory" / "rules.md",
        "# Rules\n\nAlways write tests.\n",
    )

    # Ingest log
    _write(
        root / "memory" / "ingest_log.jsonl",
        json.dumps({
            "ts": "2026-04-07T10:00:00Z",
            "source_type": "error_record",
            "project": "synapse-network",
            "id": "ERR-2026-0312-001",
            "status": "ok",
        }) + "\n",
    )
    _write(
        root / "memory" / "projects.md",
        textwrap.dedent("""\
            # Project Registry

            ## synapse-network

            - **id**: synapse-network
            - **root**: /tmp/synapse-network
            - **active**: true

            ## 注册新项目

            ### <project-id>

            - **id**: <project-id>
            - **root**: /tmp/template
            - **active**: true
        """),
    )


def _make_client(root: Path) -> TestClient:
    """Set AGENTS_MEMORY_ROOT and return a fresh TestClient."""
    os.environ["AGENTS_MEMORY_ROOT"] = str(root)
    # Force reimport of api module so AppContext picks up new env var
    import importlib
    import agents_memory.web.api as api_mod
    importlib.reload(api_mod)
    return TestClient(api_mod.app)


# ---------------------------------------------------------------------------
# Phase 1 — Core read endpoints
# ---------------------------------------------------------------------------


class TestPhase1(unittest.TestCase):
    """GET /api/stats, /api/wiki, /api/wiki/:topic, /api/wiki/lint, /api/errors, /api/rules."""

    def setUp(self) -> None:
        import tempfile
        self._tmpdir = tempfile.mkdtemp()
        self._root = Path(self._tmpdir)
        _build_env(self._root)
        self._client = _make_client(self._root)

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_stats_returns_counts(self) -> None:
        r = self._client.get("/api/stats")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("wiki_count", data)
        self.assertIn("error_count", data)
        self.assertIn("ingest_count", data)
        self.assertEqual(data["wiki_count"], 3)
        self.assertEqual(data["error_count"], 1)

    def test_stats_has_projects(self) -> None:
        r = self._client.get("/api/stats")
        data = r.json()
        self.assertIsInstance(data["projects"], list)
        self.assertEqual(data["projects"], ["synapse-network"])

    def test_wiki_list_all_topics(self) -> None:
        r = self._client.get("/api/wiki")
        self.assertEqual(r.status_code, 200)
        topics = r.json()["topics"]
        slugs = [t["topic"] for t in topics]
        self.assertIn("auth-design", slugs)
        self.assertIn("synapse-architecture", slugs)
        self.assertIn("billing-recharge", slugs)

    def test_wiki_list_has_required_fields(self) -> None:
        r = self._client.get("/api/wiki")
        self.assertIn("total", r.json())
        self.assertIn("page", r.json())
        self.assertIn("page_size", r.json())
        self.assertIn("total_pages", r.json())
        for t in r.json()["topics"]:
            self.assertIn("topic", t)
            self.assertIn("title", t)
            self.assertIn("word_count", t)
            self.assertIn("project", t)
            self.assertIsInstance(t["word_count"], int)

    def test_wiki_list_supports_pagination(self) -> None:
        r = self._client.get("/api/wiki?page=2&page_size=2")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["page"], 2)
        self.assertEqual(data["page_size"], 2)
        self.assertEqual(data["total"], 3)
        self.assertEqual(data["total_pages"], 2)
        self.assertEqual(len(data["topics"]), 1)

    def test_wiki_list_supports_full_text_query(self) -> None:
        r = self._client.get("/api/wiki?q=充值")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["query"], "充值")
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["topics"][0]["topic"], "billing-recharge")

    def test_wiki_detail_ok(self) -> None:
        r = self._client.get("/api/wiki/auth-design")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["topic"], "auth-design")
        self.assertIn("content_html", data)
        self.assertGreater(len(data["content_html"]), 0)
        self.assertIn("<h1", data["content_html"])  # toc ext adds id attribute

    def test_wiki_detail_not_found(self) -> None:
        r = self._client.get("/api/wiki/nonexistent-topic-xyz")
        self.assertEqual(r.status_code, 404)
        self.assertIn("not found", r.json()["detail"].lower())

    def test_wiki_detail_has_frontmatter(self) -> None:
        r = self._client.get("/api/wiki/auth-design")
        data = r.json()
        self.assertIsInstance(data["frontmatter"], dict)
        self.assertIn("updated_at", data["frontmatter"])

    def test_wiki_detail_returns_relationships(self) -> None:
        r = self._client.get("/api/wiki/synapse-architecture")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["project"], "synapse-network")
        self.assertEqual(data["source_path"], "docs/architecture/overview.md")
        self.assertTrue(any(link["topic"] == "auth-design" for link in data["backlinks"]))
        self.assertTrue(any(link["topic"] == "billing-recharge" for link in data["related_topics"]))

    def test_wiki_lint_returns_list(self) -> None:
        r = self._client.get("/api/wiki/lint")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("issues", data)
        self.assertIsInstance(data["issues"], list)
        self.assertIn("total", data)

    def test_wiki_lint_empty_dir(self) -> None:
        """lint should work on empty wiki dir — not 500."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            empty_root = Path(td)
            _write(empty_root / "templates" / "index.example.md", "")
            _write(empty_root / "templates" / "projects.example.md", "")
            _write(empty_root / "templates" / "rules.example.md", "")
            client = _make_client(empty_root)
            r = client.get("/api/wiki/lint")
            self.assertEqual(r.status_code, 200)
            data = r.json()
            self.assertEqual(data["total"], 0)
            self.assertEqual(data["issues"], [])

    def test_errors_list_default(self) -> None:
        r = self._client.get("/api/errors")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("errors", data)
        self.assertIsInstance(data["errors"], list)
        self.assertGreaterEqual(len(data["errors"]), 1)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["page_size"], 20)
        self.assertGreaterEqual(data["total_pages"], 1)

    def test_errors_list_supports_pagination(self) -> None:
        _write(
            self._root / "errors" / "ERR-2026-0315-001.md",
            textwrap.dedent("""\
                ---
                id: ERR-2026-0315-001
                title: Extra failure one
                status: open
                project: synapse-network
                severity: high
                date: 2026-03-15
                category: auth
                domain: backend
                source_type: error_record
                ---

                ## Problem
                Extra failure one.
            """),
        )
        _write(
            self._root / "errors" / "ERR-2026-0315-002.md",
            textwrap.dedent("""\
                ---
                id: ERR-2026-0315-002
                title: Extra failure two
                status: open
                project: synapse-network
                severity: high
                date: 2026-03-15
                category: auth
                domain: backend
                source_type: error_record
                ---

                ## Problem
                Extra failure two.
            """),
        )

        r = self._client.get("/api/errors?page=2&page_size=2")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["page"], 2)
        self.assertEqual(data["page_size"], 2)
        self.assertEqual(data["total"], 3)
        self.assertEqual(data["total_pages"], 2)
        self.assertEqual(len(data["errors"]), 1)

    def test_wiki_graph_returns_explicit_and_inferred_edges(self) -> None:
        r = self._client.get("/api/wiki/graph")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        edges = data["edges"]
        nodes = {node["id"]: node for node in data["nodes"]}
        self.assertIn("entity:synapse-network", nodes)
        self.assertEqual(nodes["decision:synapse-architecture"]["node_type"], "decision")
        self.assertEqual(nodes["decision:synapse-architecture"]["primary_topic"], "synapse-architecture")
        self.assertTrue(any(edge["type"] == "explicit" and edge["source"] == "decision:auth-design" and edge["target"] == "decision:synapse-architecture" for edge in edges))
        self.assertTrue(any(edge["type"] == "inferred" and edge["source"] == "decision:synapse-architecture" and edge["target"] == "module:billing-recharge" for edge in edges))

    def test_errors_list_status_filter(self) -> None:
        r = self._client.get("/api/errors?status=open")
        self.assertEqual(r.status_code, 200)
        for e in r.json()["errors"]:
            self.assertEqual(e["status"], "open")

    def test_errors_list_project_filter(self) -> None:
        r = self._client.get("/api/errors?project=synapse-network")
        self.assertEqual(r.status_code, 200)
        errors = r.json()["errors"]
        for e in errors:
            self.assertEqual(e["project"], "synapse-network")

    def test_errors_detail_ok(self) -> None:
        r = self._client.get("/api/errors/ERR-2026-0312-001")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["id"], "ERR-2026-0312-001")
        self.assertIn("content_html", data)
        self.assertGreater(len(data["content_html"]), 0)

    def test_errors_detail_not_found(self) -> None:
        r = self._client.get("/api/errors/ERR-9999-0000-999")
        self.assertEqual(r.status_code, 404)

    def test_errors_list_dedupes_duplicate_frontmatter_ids(self) -> None:
        _write(
            self._root / "errors" / "ERR-2026-0313-001.md",
            textwrap.dedent("""\
                ---
                id: TASK-24-FAIL
                title: Duplicate failure
                status: open
                project: synapse-network
                severity: high
                date: 2026-03-13
                category: auth
                domain: backend
                source_type: error_record
                ---

                ## Problem
                Duplicate failure newer.
            """),
        )
        _write(
            self._root / "errors" / "ERR-2026-0312-002.md",
            textwrap.dedent("""\
                ---
                id: TASK-24-FAIL
                title: Duplicate failure
                status: open
                project: synapse-network
                severity: high
                date: 2026-03-12
                category: auth
                domain: backend
                source_type: error_record
                ---

                ## Problem
                Duplicate failure older.
            """),
        )

        r = self._client.get("/api/errors?project=synapse-network&limit=20")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        matched = [item for item in data["errors"] if item["id"] == "TASK-24-FAIL"]
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["created_at"], "2026-03-13")

    def test_errors_detail_resolves_frontmatter_id_when_filename_differs(self) -> None:
        _write(
            self._root / "errors" / "ERR-2026-0312-044.md",
            textwrap.dedent("""\
                ---
                id: TASK-24-FAIL
                title: Task failure
                status: open
                project: synapse-network
                severity: high
                date: 2026-03-12
                category: auth
                domain: backend
                source_type: error_record
                ---

                ## Problem
                Legacy file name does not match frontmatter id.
            """),
        )

        r = self._client.get("/api/errors/TASK-24-FAIL")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["id"], "TASK-24-FAIL")
        self.assertIn("Legacy file name does not match frontmatter id.", data["raw"])

    def test_errors_list_replaces_generic_step_title_with_meaningful_line(self) -> None:
        _write(
            self._root / "errors" / "ERR-2026-0316-001.md",
            textwrap.dedent("""\
                ---
                id: ERR-2026-0316-001
                title: "## Step"
                status: open
                project: synapse-network
                severity: high
                date: 2026-03-16
                category: auth
                domain: backend
                source_type: error_record
                ---

                ## Step

                Refresh token callback returns 401 after Redis flush.
            """),
        )

        r = self._client.get("/api/errors?project=synapse-network&limit=20")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        matched = next(item for item in data["errors"] if item["id"] == "ERR-2026-0316-001")
        self.assertEqual(matched["title"], "Refresh token callback returns 401 after Redis flush.")

    def test_rules_ok(self) -> None:
        r = self._client.get("/api/rules")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("raw", data)
        self.assertIn("content_html", data)
        self.assertGreater(len(data["raw"]), 0)

    def test_rules_missing_graceful(self) -> None:
        """rules.md missing should not 500."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            empty_root = Path(td)
            _write(empty_root / "templates" / "index.example.md", "")
            _write(empty_root / "templates" / "projects.example.md", "")
            _write(empty_root / "templates" / "rules.example.md", "")
            client = _make_client(empty_root)
            r = client.get("/api/rules")
            self.assertEqual(r.status_code, 200)


# ---------------------------------------------------------------------------
# Phase 2 — Search + write endpoints
# ---------------------------------------------------------------------------


class TestPhase2(unittest.TestCase):
    """GET /api/search, POST /api/ingest, PUT /api/wiki/:topic, GET /api/ingest/log."""

    def setUp(self) -> None:
        import tempfile
        self._tmpdir = tempfile.mkdtemp()
        self._root = Path(self._tmpdir)
        _build_env(self._root)
        self._client = _make_client(self._root)

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_search_keyword_hits_wiki(self) -> None:
        r = self._client.get("/api/search?q=jwt&mode=keyword")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("results", data)
        self.assertIsInstance(data["results"], list)
        self.assertGreater(data["total"], 0)
        ids = [x["id"] for x in data["results"]]
        self.assertIn("auth-design", ids)

    def test_search_hybrid_returns_results(self) -> None:
        r = self._client.get("/api/search?q=architecture&mode=hybrid")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("results", data)

    def test_search_semantic_returns_wiki_results(self) -> None:
        r = self._client.get("/api/search?q=jwt refresh&mode=semantic")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        ids = [item["id"] for item in data["results"]]
        self.assertIn("auth-design", ids)

    def test_search_missing_q_returns_422(self) -> None:
        r = self._client.get("/api/search")
        self.assertEqual(r.status_code, 422)

    def test_search_response_has_required_fields(self) -> None:
        r = self._client.get("/api/search?q=test")
        data = r.json()
        self.assertIn("query", data)
        self.assertIn("mode", data)
        self.assertIn("results", data)
        self.assertIn("total", data)
        if data["results"]:
            self.assertIn("rerank_boost", data["results"][0])
            self.assertIn("rerank_reasons", data["results"][0])
            self.assertIn("matched_concepts", data["results"][0])

    def test_ingest_dry_run(self) -> None:
        payload = {
            "content": "# Test Document\nThis is a test.",
            "source_type": "error_record",
            "project": "test-project",
            "dry_run": True,
        }
        r = self._client.post("/api/ingest", json=payload)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["dry_run"])
        self.assertFalse(data["ingested"])
        # dry_run should not create files
        created = list(self._root.glob("errors/*.md"))
        # Only the one we seeded in setUp
        self.assertEqual(len(created), 1)

    def test_ingest_creates_record(self) -> None:
        payload = {
            "content": "# New Error\nThis is a new error.",
            "source_type": "error_record",
            "project": "test-project",
            "dry_run": False,
        }
        r = self._client.post("/api/ingest", json=payload)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["ingested"])
        self.assertNotEqual(data["id"], "")
        # File should exist on disk
        record_path = self._root / "errors" / f"{data['id']}.md"
        self.assertTrue(record_path.exists())
        self.assertEqual(data["storage_kind"], "error")

    def test_ingest_task_completion_writes_workflow_record_instead_of_error(self) -> None:
        payload = {
            "content": textwrap.dedent("""\
                ---
                id: TASK-42
                title: "Apply planned changes"
                project: Synapse-Network-Growing
                source_type: task_completion
                status: completed
                created_at: 2026-04-12T10:00:00Z
                ---

                ## 执行结果

                已完成。
            """),
            "source_type": "task_completion",
            "project": "Synapse-Network-Growing",
            "dry_run": False,
        }
        r = self._client.post("/api/ingest", json=payload)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["id"], "TASK-42")
        self.assertEqual(data["storage_kind"], "workflow")
        self.assertTrue((self._root / "memory" / "workflow_records" / "TASK-42.md").exists())
        self.assertFalse((self._root / "errors" / "TASK-42.md").exists())
        errors = self._client.get("/api/errors").json()["errors"]
        self.assertFalse(any(item["id"] == "TASK-42" for item in errors))

    def test_ingest_appends_log(self) -> None:
        payload = {
            "content": "# Log test\nContent.",
            "source_type": "meeting",
            "project": "proj-a",
            "dry_run": False,
        }
        self._client.post("/api/ingest", json=payload)
        log_path = self._root / "memory" / "ingest_log.jsonl"
        lines = log_path.read_text().splitlines()
        self.assertGreater(len(lines), 1)  # original + new

    def test_wiki_put_compiled_truth(self) -> None:
        payload = {"compiled_truth": "JWT tokens expire in 1 hour."}
        r = self._client.put("/api/wiki/auth-design", json=payload)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["updated"])
        self.assertEqual(data["topic"], "auth-design")

    def test_wiki_put_not_found(self) -> None:
        payload = {"compiled_truth": "Some truth."}
        r = self._client.put("/api/wiki/nonexistent-xyz", json=payload)
        self.assertEqual(r.status_code, 404)

    def test_ingest_log_returns_list(self) -> None:
        r = self._client.get("/api/ingest/log")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("entries", data)
        self.assertIsInstance(data["entries"], list)
        self.assertGreater(len(data["entries"]), 0)

    def test_ingest_log_limit(self) -> None:
        r = self._client.get("/api/ingest/log?limit=1")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertLessEqual(len(data["entries"]), 1)

    def test_workflow_endpoint_returns_new_and_legacy_records(self) -> None:
        legacy_content = textwrap.dedent("""\
            ---
            id: REQ-9
            title: Legacy workflow summary
            project: Synapse-Network-Growing
            source_type: requirement_completion
            status: completed
            created_at: 2026-04-10T08:00:00Z
            ---

            已完成遗留需求总结。
        """)
        _write(self._root / "errors" / "ERR-legacy-workflow.md", legacy_content)
        payload = {
            "content": textwrap.dedent("""\
                ---
                id: TASK-77
                title: "Review output"
                project: Synapse-Network-Growing
                source_type: task_completion
                status: completed
                created_at: 2026-04-12T10:00:00Z
                ---

                完成 review。
            """),
            "source_type": "task_completion",
            "project": "Synapse-Network-Growing",
            "dry_run": False,
        }
        self._client.post("/api/ingest", json=payload)

        r = self._client.get("/api/workflow?project=synapse-network-growing")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        ids = [item["id"] for item in data["records"]]
        self.assertIn("TASK-77", ids)
        self.assertIn("REQ-9", ids)
        record = next(item for item in data["records"] if item["id"] == "REQ-9")
        self.assertEqual(record["storage_kind"], "legacy-error")

        detail = self._client.get("/api/workflow/TASK-77")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["project"], "synapse-network-growing")


# ---------------------------------------------------------------------------
# Phase 3 — Async task endpoints
# ---------------------------------------------------------------------------


class TestPhase3(unittest.TestCase):
    """POST /api/wiki/:topic/compile, GET /api/tasks/:task_id."""

    def setUp(self) -> None:
        import tempfile
        self._tmpdir = tempfile.mkdtemp()
        self._root = Path(self._tmpdir)
        _build_env(self._root)
        self._client = _make_client(self._root)

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_compile_returns_202_and_task_id(self) -> None:
        from unittest.mock import patch
        with patch("agents_memory.services.wiki_compile.compile_wiki_topic", return_value={"ok": True}):
            r = self._client.post("/api/wiki/auth-design/compile")
        self.assertEqual(r.status_code, 202)
        data = r.json()
        self.assertIn("task_id", data)
        self.assertNotEqual(data["task_id"], "")
        self.assertIn(data["status"], ["pending", "running", "done", "failed"])

    def test_compile_not_found_topic(self) -> None:
        r = self._client.post("/api/wiki/nonexistent-xyz/compile")
        self.assertEqual(r.status_code, 404)

    def test_task_status_exists(self) -> None:
        from unittest.mock import patch
        with patch("agents_memory.services.wiki_compile.compile_wiki_topic", return_value={}):
            r = self._client.post("/api/wiki/auth-design/compile")
        task_id = r.json()["task_id"]

        r2 = self._client.get(f"/api/tasks/{task_id}")
        self.assertEqual(r2.status_code, 200)
        data = r2.json()
        self.assertEqual(data["task_id"], task_id)
        self.assertIn(data["status"], ["pending", "running", "done", "failed"])

    def test_task_not_found(self) -> None:
        r = self._client.get("/api/tasks/nonexistent-task-id-xyz")
        self.assertEqual(r.status_code, 404)


class TestProjectOnboardingApi(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile
        self._tmpdir = tempfile.mkdtemp()
        self._root = Path(self._tmpdir)
        _build_env(self._root)
        _write(self._root / "templates" / "agents-memory-bridge.instructions.md", "root={{AGENTS_MEMORY_ROOT}}\nproject={{PROJECT_ID}}\n")
        for name in ["README.template.md", "spec.template.md", "plan.template.md", "task-graph.template.md", "validation.template.md"]:
            _write(self._root / "templates" / "planning" / name, f"# {name}\nplanning bundle\n## Acceptance Criteria\n## Change Set\n## Work Items\n## Exit Criteria\n## Required Checks\n{{{{TASK_NAME}}}}\n")
        self._client = _make_client(self._root)

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_onboarding_bootstrap_registers_project_and_ingests_docs(self) -> None:
        project_root = self._root / "Synapse-Network"
        project_root.mkdir()
        _write(project_root / "README.md", "# Synapse Network\n")
        _write(project_root / "AGENTS.md", "# AGENTS\n")
        _write(project_root / "docs" / "architecture.md", "# Architecture\n")

        response = self._client.post(
            "/api/onboarding/bootstrap",
            json={
                "project_root": str(project_root),
                "full": False,
                "ingest_wiki": True,
                "max_files": 10,
                "dry_run": False,
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["project_id"], "synapse-network")
        self.assertGreaterEqual(payload["ingested_files"], 2)
        self.assertIn("README.md", payload["discovered_files"])
        self.assertTrue(any(item["topic"] == "synapse-network-readme" for item in payload["sources"]))

        projects = self._client.get("/api/projects").json()["projects"]
        synapse = next(item for item in projects if item["id"] == "synapse-network")
        self.assertGreaterEqual(synapse["wiki_count"], 2)

        stats = self._client.get("/api/projects/synapse-network/stats").json()
        self.assertGreaterEqual(stats["wiki_count"], 2)
        self.assertGreaterEqual(stats["ingest_count"], 2)

        wiki_topics = self._client.get("/api/wiki").json()["topics"]
        self.assertTrue(any(topic["project"] == "synapse-network" for topic in wiki_topics))

    def test_onboarding_bootstrap_defaults_to_full_docs_corpus_when_max_files_omitted(self) -> None:
        project_root = self._root / "Synapse-Network"
        project_root.mkdir()
        _write(project_root / "README.md", "# Synapse Network\n")
        _write(project_root / "AGENTS.md", "# AGENTS\n")
        _write(project_root / "docs" / "architecture.md", "# Architecture\n")
        _write(project_root / "docs" / "plans" / "plan.md", "# Plan\n")
        _write(project_root / "services" / "gateway" / "README.md", "# Service README\n")

        response = self._client.post(
            "/api/onboarding/bootstrap",
            json={
                "project_root": str(project_root),
                "full": False,
                "ingest_wiki": True,
                "dry_run": False,
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(payload["ingested_files"], 4)
        self.assertIn("README.md", payload["discovered_files"])
        self.assertIn("AGENTS.md", payload["discovered_files"])
        self.assertIn("docs/architecture.md", payload["discovered_files"])
        self.assertIn("docs/plans/plan.md", payload["discovered_files"])
        self.assertNotIn("services/gateway/README.md", payload["discovered_files"])

    def test_project_wiki_nav_returns_tree_and_domain_groups(self) -> None:
        project_root = self._root / "Synapse-Network"
        project_root.mkdir()
        _write(project_root / "README.md", "# Synapse Network\n")
        _write(project_root / "AGENTS.md", "# AGENTS\n")
        _write(project_root / "docs" / "AGENTS.md", "# Docs Agents\n")
        _write(project_root / "docs" / "architecture" / "README.md", "# Architecture\n")
        _write(project_root / "docs" / "plans" / "plan.md", "# Plan\n")

        response = self._client.post(
            "/api/onboarding/bootstrap",
            json={
                "project_root": str(project_root),
                "full": False,
                "ingest_wiki": True,
                "dry_run": False,
            },
        )
        self.assertEqual(response.status_code, 200)

        nav = self._client.get("/api/projects/synapse-network/wiki-nav")
        self.assertEqual(nav.status_code, 200)
        payload = nav.json()

        self.assertEqual(payload["project_id"], "synapse-network")
        self.assertGreaterEqual(payload["total_topics"], 4)
        self.assertTrue(any(item["source_group"] == "Root Docs" for item in payload["items"]))
        self.assertTrue(any(group["label"] == "Docs Root" for group in payload["groups"]))
        self.assertTrue(any(group["label"] == "Architecture" for group in payload["groups"]))
        self.assertTrue(any(group["label"] == "Plans" for group in payload["groups"]))
        self.assertFalse(any(group["label"] == "Readme.Md" for group in payload["groups"]))
        self.assertTrue(any(node["label"] == "Root Docs" for node in payload["tree"]))
        docs_node = next(node for node in payload["tree"] if node["label"] == "docs")
        self.assertTrue(any(child["label"] == "Architecture" for child in docs_node["children"]))
        self.assertTrue(any(child["label"] == "Plans" for child in docs_node["children"]))


# ---------------------------------------------------------------------------
# Renderer unit tests
# ---------------------------------------------------------------------------


class TestRenderer(unittest.TestCase):
    """Unit tests for agents_memory/web/renderer.py."""

    def setUp(self) -> None:
        from agents_memory.web.renderer import md_to_html
        self.md_to_html = md_to_html

    def test_heading_converts_to_h1(self) -> None:
        html = self.md_to_html("# Hello World")
        self.assertIn("<h1", html)  # toc ext adds id attribute: <h1 id="hello-world">
        self.assertIn("Hello World", html)

    def test_code_block_renders(self) -> None:
        html = self.md_to_html("```python\nx = 1\n```")
        self.assertIn("<code", html)

    def test_xss_script_stripped(self) -> None:
        html = self.md_to_html("<script>alert(1)</script>")
        self.assertNotIn("<script>", html)
        self.assertNotIn("alert(1)", html)

    def test_xss_iframe_stripped(self) -> None:
        html = self.md_to_html("<iframe src='evil.com'></iframe>")
        self.assertNotIn("<iframe", html)

    def test_xss_onclick_stripped(self) -> None:
        html = self.md_to_html('<a onclick="evil()">click</a>')
        self.assertNotIn("onclick", html)

    def test_empty_string_returns_empty(self) -> None:
        html = self.md_to_html("")
        self.assertEqual(html, "")

    def test_whitespace_returns_empty(self) -> None:
        html = self.md_to_html("   \n\n  ")
        self.assertEqual(html, "")

    def test_table_renders(self) -> None:
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        html = self.md_to_html(md)
        self.assertIn("<table>", html)

    def test_link_renders(self) -> None:
        html = self.md_to_html("[GitHub](https://github.com)")
        self.assertIn("<a ", html)
        self.assertIn("https://github.com", html)


# ---------------------------------------------------------------------------
# TestExtractSnippet — extracted helper from web/api.py
# ---------------------------------------------------------------------------


class TestExtractSnippet(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self._root = Path(self._tmp.name)
        import importlib
        import agents_memory.web.api as api_mod
        importlib.reload(api_mod)
        from agents_memory.web.api import _extract_snippet
        self._extract_snippet = _extract_snippet

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write_file(self, name: str, content: str) -> str:
        p = self._root / name
        p.write_text(content, encoding="utf-8")
        return str(p)

    def test_returns_empty_for_missing_file(self):
        self.assertEqual(self._extract_snippet("/nonexistent/path.md", "query"), "")

    def test_returns_empty_for_empty_filepath(self):
        self.assertEqual(self._extract_snippet("", "query"), "")

    def test_returns_matching_line(self):
        # read_body strips frontmatter — wrap content in --- fences
        path = self._write_file(
            "test.md",
            "---\nid: test\n---\nline one\nauth token fix here\nline three",
        )
        result = self._extract_snippet(path, "auth token")
        self.assertIn("auth token", result)

    def test_returns_first_200_chars_when_no_match(self):
        body = "b" * 300
        path = self._write_file("test.md", f"---\nid: test\n---\n{body}")
        result = self._extract_snippet(path, "completely-absent")
        self.assertEqual(len(result), 200)


# ---------------------------------------------------------------------------
# TestSearchWiki — extracted helper from web/api.py
# ---------------------------------------------------------------------------


class TestSearchWiki(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self._root = Path(self._tmp.name)
        os.environ["AGENTS_MEMORY_ROOT"] = str(self._root)
        _build_env(self._root)
        import importlib
        import agents_memory.web.api as api_mod
        importlib.reload(api_mod)
        from agents_memory.web.api import _search_wiki, _get_ctx
        self._search_wiki = _search_wiki
        self._ctx = _get_ctx()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_returns_empty_for_unsupported_mode(self):
        results = self._search_wiki(self._ctx, "auth", "vector-only-unsupported")
        self.assertEqual(results, [])

    def test_finds_wiki_page_by_keyword(self):
        results = self._search_wiki(self._ctx, "jwt", "keyword")
        titles = [r.id for r in results]
        self.assertIn("auth-design", titles)

    def test_no_results_for_absent_keyword(self):
        results = self._search_wiki(self._ctx, "zzz-no-such-keyword-xyz", "keyword")
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
