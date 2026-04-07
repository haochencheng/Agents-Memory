"""tests/test_web_e2e.py — 端到端冒烟测试（页面功能验证）

验证每个 Streamlit 页面对应的 API 路径的完整请求/响应链路，
包括参数过滤、写操作副作用、异步任务状态流转等。

与 test_web_api.py 的区别:
- test_web_api.py: 单端点单元测试，快，无状态
- test_web_e2e.py: 页面级端到端冒烟，多端点组合，覆盖用户交互路径

运行:
    pytest tests/test_web_e2e.py -v
    pytest tests/test_web_e2e.py -v -k E2E
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import textwrap
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


# ─── Fixtures ─────────────────────────────────────────────────────────────────


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture(scope="module")
def tmp_root(tmp_path_factory):
    root = tmp_path_factory.mktemp("e2e_root")

    # Templates
    _write(root / "templates" / "index.example.md", "# Index\n")
    _write(root / "templates" / "projects.example.md", "# Projects\n")
    _write(root / "templates" / "rules.example.md", "# Rules\n")

    # Wiki — 3 pages covering different tags
    _write(root / "memory" / "wiki" / "auth-design.md", textwrap.dedent("""\
        ---
        topic: auth-design
        updated_at: 2026-03-01
        tags: [auth, jwt]
        ---

        # Auth Design

        JWT access tokens expire after 1 hour.
        Refresh tokens are stored in HttpOnly cookies.
    """))
    _write(root / "memory" / "wiki" / "synapse-architecture.md", textwrap.dedent("""\
        ---
        topic: synapse-architecture
        updated_at: 2026-04-01
        tags: [backend, design]
        ---

        # Synapse Architecture

        Microservices communicate via gRPC.
        Each service owns its own database schema.
    """))
    _write(root / "memory" / "wiki" / "frontend-notes.md", textwrap.dedent("""\
        ---
        topic: frontend-notes
        updated_at: 2026-04-07
        tags: [frontend, react]
        ---

        # Frontend Notes

        React components use TypeScript.
        State management via Zustand.
    """))

    # Error records — 2 open, 1 resolved
    _write(root / "errors" / "ERR-2026-0312-001.md", textwrap.dedent("""\
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

        ## Root Cause
        Redis TTL key mismatch between auth service and token store.
    """))
    _write(root / "errors" / "ERR-2026-0401-002.md", textwrap.dedent("""\
        ---
        id: ERR-2026-0401-002
        title: gRPC timeout on large payload
        status: open
        project: synapse-network
        severity: medium
        date: 2026-04-01
        category: network
        domain: backend
        ---

        ## Problem
        gRPC calls timeout when payload exceeds 4 MB default limit.
    """))
    _write(root / "errors" / "ERR-2026-0320-003.md", textwrap.dedent("""\
        ---
        id: ERR-2026-0320-003
        title: CI pipeline flaky test
        status: resolved
        project: agents-memory
        severity: low
        date: 2026-03-20
        category: testing
        domain: ci
        ---

        ## Problem
        Flaky test in test_search_service.py due to file ordering.
    """))

    # Rules
    _write(root / "memory" / "rules.md", textwrap.dedent("""\
        # Rules
        - Always write tests.
        - Use timezone-aware datetimes.
    """))

    # Ingest log — 2 entries
    for entry in [
        {"ts": "2026-04-01T10:00:00+00:00", "source_type": "pr-review",
         "project": "synapse-network", "id": "INJ-001", "status": "ok"},
        {"ts": "2026-04-07T08:30:00+00:00", "source_type": "meeting",
         "project": "agents-memory", "id": "INJ-002", "status": "ok"},
    ]:
        log_path = root / "memory" / "ingest_log.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return root


@pytest.fixture(scope="module")
def client(tmp_root):
    os.environ["AGENTS_MEMORY_ROOT"] = str(tmp_root)
    import importlib
    import agents_memory.web.api as api_mod
    importlib.reload(api_mod)
    return TestClient(api_mod.app)


# ─── 页面：概览（Dashboard）─────────────────────────────────────────────────


class TestE2EOverviewPage:
    """模拟概览页面加载：/api/stats + /api/wiki/lint"""

    def test_dashboard_stats_fully_populated(self, client):
        r = client.get("/api/stats")
        assert r.status_code == 200
        d = r.json()
        assert d["wiki_count"] == 3
        assert d["error_count"] == 3
        assert d["ingest_count"] == 2
        assert "synapse-network" in d["projects"]

    def test_dashboard_lint_shows_issues_list(self, client):
        r = client.get("/api/wiki/lint")
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d["issues"], list)
        assert isinstance(d["total"], int)

    def test_dashboard_lint_structure_per_issue(self, client):
        r = client.get("/api/wiki/lint")
        for issue in r.json()["issues"]:
            assert "topic" in issue
            assert "level" in issue
            assert "message" in issue
            assert issue["level"] in ("error", "warning", "info")


# ─── 页面：Wiki 浏览 ──────────────────────────────────────────────────────────


class TestE2EWikiPage:
    """模拟 Wiki 列表 → 详情 → 更新 compiled_truth 流程"""

    def test_wiki_list_all_three_topics(self, client):
        r = client.get("/api/wiki")
        topics = [t["topic"] for t in r.json()["topics"]]
        assert "auth-design" in topics
        assert "synapse-architecture" in topics
        assert "frontend-notes" in topics

    def test_wiki_list_contains_tags(self, client):
        r = client.get("/api/wiki")
        auth = next(t for t in r.json()["topics"] if t["topic"] == "auth-design")
        assert "auth" in auth["tags"] or "jwt" in auth["tags"]

    def test_wiki_detail_renders_html(self, client):
        r = client.get("/api/wiki/auth-design")
        assert r.status_code == 200
        d = r.json()
        assert "<h1" in d["content_html"]
        assert "JWT" in d["content_html"]

    def test_wiki_detail_includes_raw_markdown(self, client):
        r = client.get("/api/wiki/synapse-architecture")
        d = r.json()
        assert "gRPC" in d["raw"]
        assert d["word_count"] > 5

    def test_wiki_detail_404_for_unknown(self, client):
        r = client.get("/api/wiki/totally-unknown-topic-xyz")
        assert r.status_code == 404

    def test_wiki_update_compiled_truth(self, client):
        payload = {"compiled_truth": "JWT tokens use RS256, expire in 1h."}
        r = client.put("/api/wiki/auth-design", json=payload)
        assert r.status_code == 200
        assert r.json()["updated"] is True

        # Verify the update persisted
        r2 = client.get("/api/wiki/auth-design")
        assert "RS256" in r2.json()["raw"]

    def test_wiki_update_nonexistent_404(self, client):
        r = client.put("/api/wiki/nonexistent-xyz", json={"compiled_truth": "x"})
        assert r.status_code == 404


# ─── 页面：搜索 ───────────────────────────────────────────────────────────────


class TestE2ESearchPage:
    """模拟搜索页面：不同模式、多词搜索、无结果场景"""

    def test_search_jwt_hits_auth_wiki(self, client):
        r = client.get("/api/search?q=jwt&mode=keyword")
        assert r.status_code == 200
        d = r.json()
        ids = [x["id"] for x in d["results"]]
        assert "auth-design" in ids

    def test_search_grpc_hits_synapse(self, client):
        r = client.get("/api/search?q=grpc&mode=keyword")
        assert r.status_code == 200
        d = r.json()
        ids = [x["id"] for x in d["results"]]
        assert "synapse-architecture" in ids

    def test_search_result_has_type_and_score(self, client):
        r = client.get("/api/search?q=jwt")
        for result in r.json()["results"]:
            assert "type" in result
            assert result["type"] in ("wiki", "error")
            assert "score" in result
            assert isinstance(result["score"], float)

    def test_search_limit_respected(self, client):
        r = client.get("/api/search?q=test&limit=2")
        assert len(r.json()["results"]) <= 2

    def test_search_missing_query_422(self, client):
        r = client.get("/api/search")
        assert r.status_code == 422

    def test_search_hybrid_mode(self, client):
        r = client.get("/api/search?q=architecture&mode=hybrid")
        assert r.status_code == 200
        assert r.json()["mode"] == "hybrid"

    def test_search_no_results_returns_empty_list(self, client):
        r = client.get("/api/search?q=zzz_no_match_xyz_999")
        assert r.status_code == 200
        assert r.json()["total"] == 0
        assert r.json()["results"] == []


# ─── 页面：错误记录 ───────────────────────────────────────────────────────────


class TestE2EErrorsPage:
    """模拟错误记录页面：列表、状态过滤、项目过滤、详情"""

    def test_errors_list_all_three(self, client):
        r = client.get("/api/errors?limit=100")
        assert r.status_code == 200
        assert r.json()["total"] == 3

    def test_errors_filter_status_open(self, client):
        r = client.get("/api/errors?status=open")
        errors = r.json()["errors"]
        assert len(errors) == 2
        for e in errors:
            assert e["status"] == "open"

    def test_errors_filter_status_resolved(self, client):
        r = client.get("/api/errors?status=resolved")
        errors = r.json()["errors"]
        assert len(errors) == 1
        assert errors[0]["id"] == "ERR-2026-0320-003"

    def test_errors_filter_by_project(self, client):
        r = client.get("/api/errors?project=agents-memory")
        errors = r.json()["errors"]
        assert len(errors) == 1
        assert errors[0]["project"] == "agents-memory"

    def test_errors_detail_renders_html(self, client):
        r = client.get("/api/errors/ERR-2026-0312-001")
        assert r.status_code == 200
        d = r.json()
        assert "Redis" in d["content_html"] or "Redis" in d["raw"]
        assert d["project"] == "synapse-network"

    def test_errors_detail_status_field(self, client):
        r = client.get("/api/errors/ERR-2026-0320-003")
        assert r.json()["status"] == "resolved"

    def test_errors_detail_not_found(self, client):
        r = client.get("/api/errors/ERR-9999-9999-999")
        assert r.status_code == 404

    def test_errors_limit_parameter(self, client):
        r = client.get("/api/errors?limit=1")
        assert len(r.json()["errors"]) <= 1


# ─── 页面：Ingest ─────────────────────────────────────────────────────────────


class TestE2EIngestPage:
    """模拟 Ingest 页：dry_run 验证、真实写入、日志刷新"""

    def test_ingest_dry_run_no_disk_write(self, client, tmp_root):
        before_count = len(list((tmp_root / "errors").glob("*.md")))
        payload = {
            "content": "# Dry Run Test\nThis should not be written.",
            "source_type": "error_record",
            "project": "health-check",
            "dry_run": True,
        }
        r = client.post("/api/ingest", json=payload)
        assert r.status_code == 200
        assert r.json()["dry_run"] is True
        assert r.json()["ingested"] is False
        after_count = len(list((tmp_root / "errors").glob("*.md")))
        assert after_count == before_count  # nothing written

    def test_ingest_real_creates_file(self, client, tmp_root):
        payload = {
            "content": "# New Meeting Notes\nDecided to use gRPC streaming.",
            "source_type": "meeting",
            "project": "synapse-network",
            "dry_run": False,
        }
        r = client.post("/api/ingest", json=payload)
        assert r.status_code == 200
        d = r.json()
        assert d["ingested"] is True
        assert d["id"].startswith("ERR-")
        assert (tmp_root / "errors" / f"{d['id']}.md").exists()

    def test_ingest_appends_log(self, client, tmp_root):
        log_path = tmp_root / "memory" / "ingest_log.jsonl"
        before_lines = log_path.read_text().count("\n")
        payload = {
            "content": "# Log Entry\nTest log append.",
            "source_type": "decision",
            "project": "agents-memory",
            "dry_run": False,
        }
        client.post("/api/ingest", json=payload)
        after_lines = log_path.read_text().count("\n")
        assert after_lines > before_lines

    def test_ingest_log_endpoint(self, client):
        r = client.get("/api/ingest/log")
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d["entries"], list)
        assert len(d["entries"]) >= 2  # at least the 2 seeded entries

    def test_ingest_log_entry_has_required_fields(self, client):
        r = client.get("/api/ingest/log")
        for entry in r.json()["entries"]:
            assert "ts" in entry
            assert "source_type" in entry
            assert "project" in entry
            assert "id" in entry
            assert "status" in entry

    def test_ingest_log_limit(self, client):
        r = client.get("/api/ingest/log?limit=1")
        assert len(r.json()["entries"]) <= 1


# ─── 页面：Rules（通过概览访问）──────────────────────────────────────────────


class TestE2ERulesPage:
    def test_rules_returns_html_content(self, client):
        r = client.get("/api/rules")
        assert r.status_code == 200
        d = r.json()
        assert "Rules" in d["raw"]
        assert "<h1" in d["content_html"] or "<p>" in d["content_html"]
        assert d["word_count"] > 0


# ─── 异步任务流转 ─────────────────────────────────────────────────────────────


class TestE2EAsyncTask:
    """模拟 wiki-compile 异步任务：POST → task_id → GET status"""

    def test_compile_task_lifecycle(self, client):
        from unittest.mock import patch
        with patch("agents_memory.services.wiki_compile.compile_wiki_topic",
                   return_value={"compiled_truth": "JWT RS256 1h expiry."}):
            r = client.post("/api/wiki/auth-design/compile")
        assert r.status_code == 202
        task_id = r.json()["task_id"]
        assert task_id.startswith("compile-auth-design-")

        # Poll status (sync TestClient, task may already be done or still pending)
        r2 = client.get(f"/api/tasks/{task_id}")
        assert r2.status_code == 200
        d = r2.json()
        assert d["task_id"] == task_id
        assert d["status"] in ("pending", "running", "done", "failed")

    def test_task_nonexistent_404(self, client):
        r = client.get("/api/tasks/no-such-task-xyz-999")
        assert r.status_code == 404
