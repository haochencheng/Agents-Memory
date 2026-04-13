from __future__ import annotations

import json
import os
import tempfile
import textwrap
import unittest
from datetime import datetime
from pathlib import Path

from agents_memory.runtime import build_context
from agents_memory.services.scheduler import (
    create_scheduler_task_bundle,
    list_scheduler_tasks,
    load_check_runs,
    run_due_scheduler_tasks,
    save_scheduler_tasks,
    summarize_check_runs,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_project_root(project_root: Path) -> None:
    _write(project_root / "README.md", "---\ncreated_at: 2026-04-13\nupdated_at: 2026-04-13\ndoc_status: active\n---\n\n# Project\n")
    _write(project_root / "docs" / "README.md", "---\ncreated_at: 2026-04-13\nupdated_at: 2026-04-13\ndoc_status: active\n---\n\n# Docs\n")
    _write(project_root / "docs" / "product" / "ai-engineering-operating-system.md", "---\ncreated_at: 2026-04-13\nupdated_at: 2026-04-13\ndoc_status: active\n---\n\nShared Engineering Brain\nMemory\nStandards\nPlanning\nValidation\n实施状态矩阵\n")
    _write(project_root / "docs" / "architecture" / "overview.md", "---\ncreated_at: 2026-04-13\nupdated_at: 2026-04-13\ndoc_status: active\n---\n\n仓库级实现决策与技术取舍\n不重复产品定位\nAI Engineering Operating System\n仓库实现 ADR\n")
    _write(project_root / "docs" / "architecture" / "modular.md", "---\ncreated_at: 2026-04-13\nupdated_at: 2026-04-13\ndoc_status: active\n---\n\n代码目录结构与模块分层\nruntime / services / commands / integrations\n为什么这样实现\n代码如何分层与扩展\n")
    _write(project_root / "docs" / "guides" / "integration.md", "---\ncreated_at: 2026-04-13\nupdated_at: 2026-04-13\ndoc_status: active\n---\n\n目标项目如何接入\n用户执行哪些命令\n如何验证是否生效\n外部项目如何接入与验证\n")
    _write(project_root / "docs" / "guides" / "commands.md", "---\ncreated_at: 2026-04-13\nupdated_at: 2026-04-13\ndoc_status: active\n---\n\n命令签名与参数形态\n命令参考\n外部项目接入流程\n本仓库本地启动与运维\n")
    _write(project_root / "docs" / "guides" / "getting-started.md", "---\ncreated_at: 2026-04-13\nupdated_at: 2026-04-13\ndoc_status: active\n---\n\n本仓库如何克隆、安装、启动\n目标项目如何接入 Agents-Memory\n本仓库首次安装与启动\n日常运维与故障处理\n")
    _write(project_root / "docs" / "ops" / "runbook.md", "---\ncreated_at: 2026-04-13\nupdated_at: 2026-04-13\ndoc_status: active\n---\n\n日常运维命令和例行维护\n日志、索引、Qdrant、备份、排障\n本仓库如何首次安装与启动\n外部项目接入流程\n")
    _write(project_root / "docs" / "ops" / "foundation-hardening.md", "---\ncreated_at: 2026-04-13\nupdated_at: 2026-04-13\ndoc_status: active\n---\n\nBehavior change\n=> code change\n=> docs change\n=> test or validation change\n")
    _write(project_root / "docs" / "ops" / "release-checklist.md", "---\ncreated_at: 2026-04-13\nupdated_at: 2026-04-13\ndoc_status: active\n---\n\n更新 CHANGELOG.md\n.github/workflows/ci.yml\nGit tag\nGitHub Release\n")
    _write(project_root / "CONTRIBUTING.md", "---\ncreated_at: 2026-04-13\nupdated_at: 2026-04-13\ndoc_status: active\n---\n\n# Contributing\n")
    _write(project_root / "CHANGELOG.md", "# Changelog\n")
    _write(project_root / "LICENSE", "MIT\n")
    _write(project_root / "CODE_OF_CONDUCT.md", "# Code of Conduct\n")
    _write(project_root / "SECURITY.md", "# Security\n")
    _write(project_root / "SUPPORT.md", "# Support\n")
    _write(project_root / "PULL_REQUEST_TEMPLATE.md", "# Pull Request\n")
    _write(project_root / "pyproject.toml", "[project]\nname = \"demo\"\n")
    _write(project_root / ".github" / "FUNDING.yml", "github: demo\n")
    _write(project_root / ".github" / "workflows" / "ci.yml", "tests:\npython -m pip install .\npython -m py_compile\npython -m unittest discover -s tests -p 'test_*.py'\ndocs:\npython -m pip install .\npython scripts/memory.py docs-check .\n")
    _write(project_root / ".github" / "ISSUE_TEMPLATE" / "bug_report.md", "# Bug\n")
    _write(project_root / ".github" / "ISSUE_TEMPLATE" / "feature_request.md", "# Feature\n")
    _write(project_root / "tests" / "test_runtime_bootstrap.py", "def test_runtime_bootstrap():\n    assert True\n")
    _write(project_root / "tests" / "test_projects_service.py", "def test_projects_service():\n    assert True\n")
    _write(project_root / "tests" / "test_records_service.py", "def test_records_service():\n    assert True\n")
    _write(project_root / "tests" / "test_integration_service.py", "def test_integration_service():\n    assert True\n")
    _write(project_root / "tests" / "test_planning_service.py", "def test_planning_service():\n    assert True\n")
    _write(project_root / "tests" / "test_docs_check.py", "def test_docs_check():\n    assert True\n")
    _write(project_root / "standards" / "validation" / "docs-check.rules.md", "docs entrypoint 完整\n文档元数据完整\n核心 services 有单元测试\n行为变更必须同时看到 code diff、docs diff、test diff 中至少两层联动\n")
    _write(project_root / "standards" / "planning" / "harness-engineering.md", "docs、code、validation\nplan / task graph / validation route\n文档元数据\n")
    _write(project_root / "standards" / "planning" / "review-checklist.md", "docs / code / tests\n最小验证结果\n")
    _write(project_root / "standards" / "planning" / "spec-kit.md", "spec-first\n验收标准必须可被测试或命令验证\n")
    _write(project_root / "standards" / "python" / "base.instructions.md", "复杂度\n重构\n40 行\n嵌套深度\n注释\n")
    _write(project_root / ".agents-memory" / "profile-manifest.json", json.dumps({"profile_id": "agent-runtime"}, ensure_ascii=False))
    _write(project_root / ".agents-memory" / "project-facts.json", json.dumps({"variables": {}, "facts": {}, "detectors": []}, ensure_ascii=False))
    _write(project_root / "docs" / "plans" / "demo-task" / "README.md", "---\ncreated_at: 2026-04-13\nupdated_at: 2026-04-13\ndoc_status: active\n---\n\nplanning bundle\n")
    _write(project_root / "docs" / "plans" / "demo-task" / "spec.md", "---\ncreated_at: 2026-04-13\nupdated_at: 2026-04-13\ndoc_status: active\n---\n\n## Acceptance Criteria\n- done\n")
    _write(project_root / "docs" / "plans" / "demo-task" / "plan.md", "---\ncreated_at: 2026-04-13\nupdated_at: 2026-04-13\ndoc_status: active\n---\n\n## Change Set\n- change\n")
    _write(project_root / "docs" / "plans" / "demo-task" / "task-graph.md", "---\ncreated_at: 2026-04-13\nupdated_at: 2026-04-13\ndoc_status: active\n---\n\n## Work Items\n- work\n\n## Exit Criteria\n- [x] done\n")
    _write(project_root / "docs" / "plans" / "demo-task" / "validation.md", "---\ncreated_at: 2026-04-13\nupdated_at: 2026-04-13\ndoc_status: active\n---\n\n## Required Checks\n- docs\n")


def _build_runtime_root(root: Path, project_root: Path) -> None:
    _write(root / "templates" / "index.example.md", "# Index\n")
    _write(root / "templates" / "projects.example.md", "# Projects\n")
    _write(root / "templates" / "rules.example.md", "# Rules\n")
    _write(
        root / "memory" / "projects.md",
        textwrap.dedent(
            f"""\
            # Project Registry

            ## synapse-network

            - **id**: synapse-network
            - **root**: {project_root}
            - **active**: true
            """
        ),
    )


class TestSchedulerService(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._root = Path(self._tmpdir.name)
        self._project_root = self._root / "synapse-network"
        _build_project_root(self._project_root)
        _build_runtime_root(self._root, self._project_root)
        os.environ["AGENTS_MEMORY_ROOT"] = str(self._root)
        self._ctx = build_context(logger_name="agents_memory.tests")

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_scheduler_tasks_persist_to_disk(self) -> None:
        created = create_scheduler_task_bundle(
            self._ctx,
            name="nightly-check",
            project="synapse-network",
            cron_expr="0 2 * * *",
            now=datetime.fromisoformat("2026-04-13T01:50:00+08:00"),
        )
        self.assertEqual(len(created), 3)
        reloaded = list_scheduler_tasks(self._ctx)
        self.assertEqual(len(reloaded), 3)
        self.assertTrue(all(task.next_run for task in reloaded))

    def test_due_scheduler_tasks_write_checks_and_workflow_records(self) -> None:
        created = create_scheduler_task_bundle(
            self._ctx,
            name="nightly-check",
            project="synapse-network",
            cron_expr="0 2 * * *",
            now=datetime.fromisoformat("2026-04-13T01:50:00+08:00"),
        )
        for task in created:
            task.next_run = "2026-04-13T02:00:00+08:00"
        save_scheduler_tasks(self._ctx, created)

        runs = run_due_scheduler_tasks(self._ctx, now=datetime.fromisoformat("2026-04-13T02:00:00+08:00"))
        self.assertEqual(len(runs), 3)
        stored_runs = load_check_runs(self._ctx)
        self.assertEqual(len(stored_runs), 3)
        summary = summarize_check_runs(stored_runs)
        self.assertEqual(sum(summary["docs"].values()), 1)
        self.assertEqual(sum(summary["profile"].values()), 1)
        self.assertEqual(sum(summary["plan"].values()), 1)
        workflow_paths = sorted((self._root / "memory" / "workflow_records").glob("*.md"))
        self.assertEqual(len(workflow_paths), 3)
        for path in workflow_paths:
            content = path.read_text(encoding="utf-8")
            self.assertIn("source_type: scheduler_check", content)
            self.assertIn("# Scheduler Check Run", content)


if __name__ == "__main__":
    unittest.main()
