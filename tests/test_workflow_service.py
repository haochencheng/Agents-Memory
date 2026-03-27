from __future__ import annotations

import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from agents_memory.runtime import build_context
from agents_memory.services.workflows import WorkflowValidationReport, WorkflowValidationSection, close_task, cmd_close_task, cmd_do_next, cmd_start_task, cmd_validate


def _doc(content: str) -> str:
    if content.startswith("---\n"):
        return content
    return "\n".join(
        [
            "---",
            "created_at: 2026-03-28",
            "updated_at: 2026-03-28",
            "doc_status: active",
            "---",
            "",
            content,
        ]
    )


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".md":
        content = _doc(content)
    path.write_text(content, encoding="utf-8")


class WorkflowServiceTests(unittest.TestCase):
    def _build_context(self, root: Path):
        _write_text(root / "templates" / "index.example.md", "index\n")
        _write_text(root / "templates" / "projects.example.md", "# Project Registry\n")
        _write_text(root / "templates" / "rules.example.md", "# Promoted Rules\n")
        previous_root = os.environ.get("AGENTS_MEMORY_ROOT")
        os.environ["AGENTS_MEMORY_ROOT"] = str(root)
        try:
            return build_context(logger_name=f"tests.workflows.{root.name}", reference_file=__file__)
        finally:
            if previous_root is None:
                os.environ.pop("AGENTS_MEMORY_ROOT", None)
            else:
                os.environ["AGENTS_MEMORY_ROOT"] = previous_root

    def test_cmd_do_next_reports_pending_onboarding_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project_root = root / "demo"
            project_root.mkdir()
            _write_text(
                project_root / ".agents-memory" / "onboarding-state.json",
                json.dumps(
                    {
                        "project_bootstrap_ready": False,
                        "project_bootstrap_complete": False,
                        "runbook_steps": [
                            {
                                "group": "Integration",
                                "key": "mcp_config",
                                "priority": "required",
                                "command": "amem mcp-setup .",
                                "verify_with": "amem doctor .",
                                "done_when": "done",
                                "next_command": "amem doctor .",
                                "safe_to_auto_execute": True,
                                "approval_required": False,
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
            )
            ctx = self._build_context(root)
            buffer = StringIO()
            with redirect_stdout(buffer):
                exit_code = cmd_do_next(ctx, str(project_root))

            self.assertEqual(exit_code, 0)
            output = buffer.getvalue()
            self.assertIn("Status:    pending", output)
            self.assertIn("Command:   amem mcp-setup .", output)

    def test_cmd_validate_aggregates_existing_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project_root = root / "demo"
            project_root.mkdir()
            ctx = self._build_context(root)
            _write_text(project_root / "README.md", "# Demo\n安装与启动细节见 docs/getting-started.md\n接入其他项目见 docs/integration.md\n最新架构设计见 docs/ai-engineering-operating-system.md\n")
            _write_text(project_root / "docs" / "README.md", "- [Getting Started](getting-started.md)\n")
            _write_text(project_root / "docs" / "getting-started.md", "本仓库如何克隆、安装、启动\n目标项目如何接入 Agents-Memory\n本仓库首次安装与启动\n日常运维与故障处理\npython3 scripts/memory.py bootstrap .\npython3 scripts/memory.py do-next .\npython3 scripts/memory.py start-task sample-task .\npython3 scripts/memory.py validate .\n")
            _write_text(project_root / "docs" / "integration.md", "目标项目如何接入\n用户执行哪些命令\n如何验证是否生效\n外部项目如何接入与验证\n")
            _write_text(project_root / "docs" / "commands.md", "命令签名与参数形态\n命令参考\n外部项目接入流程\n本仓库本地启动与运维\n")
            _write_text(project_root / "docs" / "ops.md", "日常运维命令和例行维护\n日志、索引、Qdrant、备份、排障\n本仓库如何首次安装与启动\n外部项目接入流程\n")
            _write_text(project_root / "docs" / "ai-engineering-operating-system.md", "Shared Engineering Brain\nMemory\nStandards\nPlanning\nValidation\n实施状态矩阵\n")
            _write_text(project_root / "docs" / "architecture.md", "仓库级实现决策与技术取舍\n不重复产品定位\nAI Engineering Operating System\n仓库实现 ADR\n")
            _write_text(project_root / "docs" / "modular-architecture.md", "代码目录结构与模块分层\nruntime / services / commands / integrations\n为什么这样实现\n代码如何分层与扩展\n")
            _write_text(project_root / "docs" / "foundation-hardening.md", "Behavior change\n=> code change\n=> docs change\n=> test or validation change\n")
            _write_text(project_root / "llms.txt", "python3 scripts/memory.py bootstrap [path] [--full]\npython3 scripts/memory.py do-next [path]\npython3 scripts/memory.py start-task <task-name> [path]\npython3 scripts/memory.py validate [path]\n")
            _write_text(project_root / "CHANGELOG.md", "# Changelog\n")
            _write_text(project_root / "CONTRIBUTING.md", "# Contributing\n")
            _write_text(project_root / "LICENSE", "MIT\n")
            _write_text(project_root / "CODE_OF_CONDUCT.md", "# Code of Conduct\n")
            _write_text(project_root / "SECURITY.md", "# Security\n")
            _write_text(project_root / "SUPPORT.md", "# Support\n")
            _write_text(project_root / "PULL_REQUEST_TEMPLATE.md", "# PR\n")
            _write_text(project_root / "docs" / "release-checklist.md", "更新 CHANGELOG.md\n.github/workflows/ci.yml\nGit tag\nGitHub Release\n")
            _write_text(project_root / ".github" / "FUNDING.yml", "github: [demo]\n")
            _write_text(project_root / ".github" / "workflows" / "ci.yml", "tests:\npython -m pip install .\npython -m py_compile\npython -m unittest discover -s tests -p 'test_*.py'\ndocs:\npython -m pip install .\npython scripts/memory.py docs-check .\n")
            _write_text(project_root / ".github" / "ISSUE_TEMPLATE" / "bug_report.md", "bug\n")
            _write_text(project_root / ".github" / "ISSUE_TEMPLATE" / "feature_request.md", "feature\n")
            _write_text(project_root / "standards" / "docs" / "docs-sync.instructions.md", "docs\ncode\ntests\ncreated_at\nupdated_at\ndoc_status\n")
            _write_text(project_root / "standards" / "validation" / "docs-check.rules.md", "docs entrypoint 完整\n文档元数据完整\n核心 services 有单元测试\n行为变更必须同时看到 code diff、docs diff、test diff 中至少两层联动\n")
            _write_text(project_root / "standards" / "planning" / "harness-engineering.md", "docs、code、validation\nplan / task graph / validation route\n文档元数据\n")
            _write_text(project_root / "standards" / "planning" / "review-checklist.md", "docs / code / tests\n最小验证结果\n")
            _write_text(project_root / "standards" / "planning" / "spec-kit.md", "spec-first\n验收标准必须可被测试或命令验证\n")
            _write_text(project_root / "standards" / "python" / "base.instructions.md", "复杂度\n重构\n40 行\n嵌套深度\n注释\n")
            _write_text(project_root / "tests" / "test_runtime_bootstrap.py", "pass\n")
            _write_text(project_root / "tests" / "test_projects_service.py", "pass\n")
            _write_text(project_root / "tests" / "test_records_service.py", "pass\n")
            _write_text(project_root / "tests" / "test_integration_service.py", "pass\n")
            _write_text(project_root / "tests" / "test_planning_service.py", "pass\n")
            _write_text(project_root / "tests" / "test_docs_check.py", "pass\n")
            _write_text(project_root / "docs" / "plans" / "demo-task" / "README.md", "planning bundle\n")
            _write_text(project_root / "docs" / "plans" / "demo-task" / "spec.md", "## Acceptance Criteria\n")
            _write_text(project_root / "docs" / "plans" / "demo-task" / "plan.md", "## Change Set\n")
            _write_text(project_root / "docs" / "plans" / "demo-task" / "task-graph.md", "## Work Items\n## Exit Criteria\n")
            _write_text(project_root / "docs" / "plans" / "demo-task" / "validation.md", "## Required Checks\n")

            buffer = StringIO()
            with redirect_stdout(buffer):
                exit_code = cmd_validate(ctx, str(project_root))

            self.assertEqual(exit_code, 1)
            output = buffer.getvalue()
            self.assertIn("=== Validate ===", output)
            self.assertIn("[docs]", output)
            self.assertIn("[planning] OK", output)
            self.assertIn("[doctor]", output)

    def test_cmd_start_task_persists_active_task_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project_root = root / "demo"
            project_root.mkdir()
            ctx = self._build_context(root)
            for name in ["README.template.md", "spec.template.md", "plan.template.md", "task-graph.template.md", "validation.template.md"]:
                _write_text(root / "templates" / "planning" / name, f"# {name}\n{{{{TASK_NAME}}}}\n{{{{TASK_SLUG}}}}\n")

            buffer = StringIO()
            with redirect_stdout(buffer):
                exit_code = cmd_start_task(ctx, "Close Task Flow", str(project_root))

            self.assertEqual(exit_code, 0)
            state = json.loads((project_root / ".agents-memory" / "onboarding-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["active_task"]["task_slug"], "close-task-flow")
            self.assertEqual(state["last_started_task"]["status"], "active")

    def test_cmd_do_next_surfaces_active_task_hint(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project_root = root / "demo"
            project_root.mkdir()
            _write_text(
                project_root / ".agents-memory" / "onboarding-state.json",
                json.dumps(
                    {
                        "project_bootstrap_ready": True,
                        "project_bootstrap_complete": True,
                        "runbook_steps": [],
                        "recommended_steps": [],
                        "active_task": {
                            "task_name": "Close Task Flow",
                            "task_slug": "close-task-flow",
                            "bundle_path": "docs/plans/close-task-flow",
                            "status": "active",
                            "started_at": "2026-03-28T00:00:00+00:00",
                        },
                    },
                    ensure_ascii=False,
                ),
            )
            ctx = self._build_context(root)
            buffer = StringIO()
            with redirect_stdout(buffer):
                exit_code = cmd_do_next(ctx, str(project_root))

            self.assertEqual(exit_code, 0)
            output = buffer.getvalue()
            self.assertIn("ActiveTask: close-task-flow", output)
            self.assertIn("Close:      amem close-task . --slug close-task-flow", output)

    def test_cmd_close_task_updates_bundle_and_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project_root = root / "demo"
            project_root.mkdir()
            ctx = self._build_context(root)
            bundle_root = project_root / "docs" / "plans" / "close-task-flow"
            _write_text(bundle_root / "README.md", "# Close Task Flow\nplanning bundle\n")
            _write_text(bundle_root / "task-graph.md", "# Task Graph\n\n## Work Items\n1. item\n\n## Exit Criteria\n- done\n")
            _write_text(bundle_root / "validation.md", "# Validation Route\n\n## Required Checks\n- check\n")
            _write_text(
                project_root / ".agents-memory" / "onboarding-state.json",
                json.dumps(
                    {
                        "project_bootstrap_ready": True,
                        "project_bootstrap_complete": True,
                        "active_task": {
                            "task_name": "Close Task Flow",
                            "task_slug": "close-task-flow",
                            "bundle_path": "docs/plans/close-task-flow",
                            "status": "active",
                            "started_at": "2026-03-28T00:00:00+00:00",
                        },
                        "recommended_steps": [
                            {
                                "key": "refactor_bundle",
                                "task_slug": "close-task-flow",
                                "bundle_path": "docs/plans/close-task-flow",
                                "command": "amem refactor-bundle .",
                                "verify_with": "amem doctor .",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
            )
            report = WorkflowValidationReport(
                project_root=project_root,
                overall="OK",
                sections=[WorkflowValidationSection(name="docs", overall="OK", findings=[])],
            )

            with patch("agents_memory.services.workflows.collect_workflow_validation_report", return_value=report):
                buffer = StringIO()
                with redirect_stdout(buffer):
                    exit_code = cmd_close_task(ctx, str(project_root), task_slug="close-task-flow")

            self.assertEqual(exit_code, 0)
            self.assertIn("## Task Status", (bundle_root / "README.md").read_text(encoding="utf-8"))
            self.assertIn('"status": "completed"', (bundle_root / "task-graph.md").read_text(encoding="utf-8"))
            self.assertIn("## Close-Out Summary", (bundle_root / "validation.md").read_text(encoding="utf-8"))

            state = json.loads((project_root / ".agents-memory" / "onboarding-state.json").read_text(encoding="utf-8"))
            self.assertNotIn("active_task", state)
            self.assertEqual(state["last_completed_task"]["task_slug"], "close-task-flow")
            self.assertEqual(state["completed_tasks"][0]["status"], "completed")
            self.assertNotIn("recommended_steps", state)

    def test_bundle_gate_warns_on_unchecked_exit_criteria(self) -> None:
        from agents_memory.services.validation import collect_bundle_exit_criteria_findings

        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_root = Path(tmpdir) / "docs" / "plans" / "my-task"
            _write_text(bundle_root / "task-graph.md", "# Task Graph\n\n## Exit Criteria\n\n- [ ] must pass CI\n")
            _write_text(bundle_root / "validation.md", "# Validation\n\n## Required Checks\n")

            findings = collect_bundle_exit_criteria_findings(bundle_root)

            self.assertTrue(any(f.status == "WARN" and f.key == "exit_criteria_unchecked" for f in findings))

    def test_bundle_gate_passes_when_all_criteria_checked(self) -> None:
        from agents_memory.services.validation import collect_bundle_exit_criteria_findings

        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_root = Path(tmpdir) / "docs" / "plans" / "my-task"
            _write_text(bundle_root / "task-graph.md", "# Task Graph\n\n## Exit Criteria\n\n- [x] CI green\n")
            _write_text(bundle_root / "validation.md", "# Validation\n\n## Task-Specific Checks\n\n- [x] docs updated\n")

            findings = collect_bundle_exit_criteria_findings(bundle_root)

            self.assertFalse(any(f.status == "WARN" for f in findings))
            self.assertTrue(any(f.status == "OK" for f in findings))

    def test_bundle_gate_passes_when_no_checkboxes(self) -> None:
        from agents_memory.services.validation import collect_bundle_exit_criteria_findings

        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_root = Path(tmpdir) / "docs" / "plans" / "my-task"
            _write_text(bundle_root / "task-graph.md", "# Task Graph\n\n## Exit Criteria\n\n- 任务完成时必须满足哪些条件？\n")
            _write_text(bundle_root / "validation.md", "# Validation\n\n## Required Checks\n")

            findings = collect_bundle_exit_criteria_findings(bundle_root)

            self.assertFalse(any(f.status == "WARN" for f in findings))
            self.assertTrue(any(f.status == "OK" and f.key == "bundle_gate" for f in findings))

    def test_close_task_blocks_when_bundle_gate_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project_root = root / "demo"
            project_root.mkdir()
            ctx = self._build_context(root)
            bundle_root = project_root / "docs" / "plans" / "my-task"
            _write_text(bundle_root / "README.md", "# My Task\n")
            _write_text(bundle_root / "task-graph.md", "# Task Graph\n\n## Exit Criteria\n\n- [ ] unchecked requirement\n")
            _write_text(bundle_root / "validation.md", "# Validation\n\n## Required Checks\n")

            with self.assertRaises(RuntimeError) as cm:
                close_task(ctx, str(project_root), task_slug="my-task")

            self.assertIn("bundle exit criteria gate failed", str(cm.exception))

    def test_close_task_skip_global_gate_bypasses_repo_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project_root = root / "demo"
            project_root.mkdir()
            ctx = self._build_context(root)
            bundle_root = project_root / "docs" / "plans" / "my-task"
            _write_text(bundle_root / "README.md", "# My Task\n")
            _write_text(bundle_root / "task-graph.md", "# Task Graph\n\n## Exit Criteria\n- done\n")
            _write_text(bundle_root / "validation.md", "# Validation\n\n## Required Checks\n")

            failing_report = WorkflowValidationReport(
                project_root=project_root,
                overall="FAIL",
                sections=[WorkflowValidationSection(name="docs", overall="FAIL", findings=[])],
            )
            with patch("agents_memory.services.workflows.collect_workflow_validation_report", return_value=failing_report):
                result = close_task(ctx, str(project_root), task_slug="my-task", skip_global_gate=True)

            self.assertEqual(result.task_slug, "my-task")
            self.assertTrue(result.skip_global_gate)
            self.assertEqual(result.bundle_gate_section.overall, "OK")
