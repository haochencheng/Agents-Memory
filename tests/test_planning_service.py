from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from agents_memory.runtime import build_context
from agents_memory.services.planning import cmd_refactor_bundle, init_onboarding_bundle, init_plan_bundle, init_refactor_bundle, repair_plan_bundles, slugify_task_name
from agents_memory.services.validation import cmd_plan_check, collect_plan_check_findings


def _doc(content: str) -> str:
    if content.startswith("---\n"):
        return content
    return "\n".join(
        [
            "---",
            "created_at: 2026-03-27",
            "updated_at: 2026-03-27",
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


class PlanningServiceTests(unittest.TestCase):
    def _build_context(self, root: Path):
        _write_text(root / "templates" / "index.example.md", "index\n")
        _write_text(root / "templates" / "projects.example.md", "# Project Registry\n")
        _write_text(root / "templates" / "rules.example.md", "# Promoted Rules\n")
        previous_root = os.environ.get("AGENTS_MEMORY_ROOT")
        os.environ["AGENTS_MEMORY_ROOT"] = str(root)
        try:
            return build_context(logger_name=f"tests.planning.{root.name}", reference_file=__file__)
        finally:
            if previous_root is None:
                os.environ.pop("AGENTS_MEMORY_ROOT", None)
            else:
                os.environ["AGENTS_MEMORY_ROOT"] = previous_root

    def test_slugify_task_name_normalizes_text(self) -> None:
        self.assertEqual(slugify_task_name("Shared Engineering Brain"), "shared-engineering-brain")
        self.assertEqual(slugify_task_name("  "), "untitled-task")

    def test_init_plan_bundle_creates_planning_scaffold(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            ctx = self._build_context(root)
            for name in ["README.template.md", "spec.template.md", "plan.template.md", "task-graph.template.md", "validation.template.md"]:
                _write_text(root / "templates" / "planning" / name, f"# {name}\n{{{{TASK_NAME}}}}\n{{{{TASK_SLUG}}}}\n")

            result = init_plan_bundle(ctx, "Introduce Planning Layer", target)

            plan_dir = target / "docs" / "plans" / "introduce-planning-layer"
            self.assertTrue(plan_dir.exists())
            self.assertTrue((plan_dir / "spec.md").exists())
            self.assertIn("docs/plans/introduce-planning-layer/spec.md", result.wrote_files)
            self.assertIn("docs/plans/introduce-planning-layer", result.created_dirs)
            self.assertIn("Introduce Planning Layer", (plan_dir / "spec.md").read_text(encoding="utf-8"))

    def test_init_plan_bundle_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            ctx = self._build_context(root)
            _write_text(root / "templates" / "planning" / "spec.template.md", "# Spec\n{{TASK_NAME}}\n")

            result = init_plan_bundle(ctx, "Dry Run Plan", target, dry_run=True)

            self.assertFalse((target / "docs" / "plans" / "dry-run-plan").exists())
            self.assertIn("docs/plans/dry-run-plan/spec.md", result.wrote_files)
            self.assertTrue(result.dry_run)

    def test_collect_plan_check_findings_flags_missing_required_bundle_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            bundle = target / "docs" / "plans" / "demo-task"
            bundle.mkdir(parents=True)
            self._build_context(root)
            _write_text(bundle / "README.md", "# Demo\nplanning bundle\n")
            _write_text(bundle / "spec.md", "## Acceptance Criteria\n")
            _write_text(bundle / "plan.md", "## Change Set\n")
            _write_text(bundle / "validation.md", "## Required Checks\n")

            findings = collect_plan_check_findings(target, str(target))

            self.assertTrue(any(f.status == "FAIL" and f.key == "plan_files" for f in findings))

    def test_collect_plan_check_findings_flags_missing_bundle_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            bundle = target / "docs" / "plans" / "demo-task"
            bundle.mkdir(parents=True)
            self._build_context(root)
            (bundle / "README.md").write_text("# Demo\nplanning bundle\n", encoding="utf-8")
            _write_text(bundle / "spec.md", "## Acceptance Criteria\n")
            _write_text(bundle / "plan.md", "## Change Set\n")
            _write_text(bundle / "task-graph.md", "## Work Items\n## Exit Criteria\n")
            _write_text(bundle / "validation.md", "## Required Checks\n")

            findings = collect_plan_check_findings(target, str(target))

            self.assertTrue(any(f.status == "FAIL" and f.key == "plan_metadata" for f in findings))

    def test_repair_plan_bundles_creates_missing_files_for_existing_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            bundle = target / "docs" / "plans" / "completed"
            bundle.mkdir(parents=True)
            ctx = self._build_context(root)
            for name in ["README.template.md", "spec.template.md", "plan.template.md", "task-graph.template.md", "validation.template.md"]:
                _write_text(root / "templates" / "planning" / name, f"# {name}\nplanning bundle\n## Acceptance Criteria\n## Change Set\n## Work Items\n## Exit Criteria\n## Required Checks\n{{{{TASK_NAME}}}}\n")
            _write_text(bundle / "spec.md", "## Acceptance Criteria\n")
            _write_text(bundle / "plan.md", "## Change Set\n")
            _write_text(bundle / "task-graph.md", "## Work Items\n## Exit Criteria\n")
            _write_text(bundle / "validation.md", "## Required Checks\n")

            result = repair_plan_bundles(ctx, target)

            self.assertTrue((bundle / "README.md").exists())
            self.assertIn("docs/plans/completed/README.md", result.repaired_files)

    def test_init_onboarding_bundle_uses_exported_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            ctx = self._build_context(root)
            for name in ["README.template.md", "spec.template.md", "plan.template.md", "task-graph.template.md", "validation.template.md"]:
                _write_text(root / "templates" / "planning" / name, f"# {name}\n{{{{TASK_NAME}}}}\n{{{{TASK_SLUG}}}}\n")
            _write_text(
                target / ".agents-memory" / "onboarding-state.json",
                "\n".join(
                    [
                        "{",
                        '  "project_bootstrap_ready": false,',
                        '  "project_bootstrap_complete": false,',
                        '  "recommended_next_group": "Integration",',
                        '  "recommended_next_key": "mcp_config",',
                        '  "recommended_next_command": "amem mcp-setup .",',
                        '  "recommended_verify_command": "amem doctor .",',
                        '  "recommended_done_when": "`amem doctor .` shows `[OK] mcp_config`.",',
                        '  "action_sequence": ["Integration (required): Run `amem mcp-setup .`"],',
                        '  "runbook_steps": [{"group": "Integration", "key": "mcp_config"}],',
                        '  "groups": [{"name": "Integration", "status": "ATTENTION"}]',
                        "}",
                    ]
                ),
            )

            result = init_onboarding_bundle(ctx, target)

            plan_dir = target / "docs" / "plans" / "onboarding-mcp-config"
            self.assertTrue(plan_dir.exists())
            self.assertEqual(result.recommended_next_command, "amem mcp-setup .")
            self.assertIn("amem mcp-setup .", (plan_dir / "plan.md").read_text(encoding="utf-8"))
            self.assertIn("project_bootstrap_ready", (plan_dir / "validation.md").read_text(encoding="utf-8"))
            self.assertNotIn(str(target), (plan_dir / "spec.md").read_text(encoding="utf-8"))

    def test_init_onboarding_bundle_refreshes_managed_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            ctx = self._build_context(root)
            for name in ["README.template.md", "spec.template.md", "plan.template.md", "task-graph.template.md", "validation.template.md"]:
                _write_text(root / "templates" / "planning" / name, f"# {name}\n{{{{TASK_NAME}}}}\n{{{{TASK_SLUG}}}}\n")
            state_path = target / ".agents-memory" / "onboarding-state.json"
            _write_text(
                state_path,
                json.dumps(
                    {
                        "project_bootstrap_ready": False,
                        "project_bootstrap_complete": False,
                        "recommended_next_group": "Integration",
                        "recommended_next_key": "mcp_config",
                        "recommended_next_command": "amem mcp-setup .",
                        "recommended_verify_command": "amem doctor .",
                        "recommended_done_when": "done-1",
                        "action_sequence": ["step-1"],
                        "runbook_steps": [{"group": "Integration", "key": "mcp_config"}],
                        "groups": [{"name": "Integration", "status": "ATTENTION"}],
                    },
                    ensure_ascii=False,
                ),
            )

            first = init_onboarding_bundle(ctx, target)
            plan_file = first.plan_root / "plan.md"
            original = plan_file.read_text(encoding="utf-8")
            customized = original.replace("## Onboarding Execution", "Custom note\n\n## Onboarding Execution", 1)
            plan_file.write_text(customized, encoding="utf-8")
            _write_text(
                state_path,
                json.dumps(
                    {
                        "project_bootstrap_ready": False,
                        "project_bootstrap_complete": False,
                        "recommended_next_group": "Planning",
                        "recommended_next_key": "planning_root",
                        "recommended_next_command": 'amem plan-init "task" .',
                        "recommended_verify_command": "amem plan-check .",
                        "recommended_done_when": "done-2",
                        "action_sequence": ["step-2"],
                        "runbook_steps": [{"group": "Planning", "key": "planning_root"}],
                        "groups": [{"name": "Planning", "status": "WATCH"}],
                    },
                    ensure_ascii=False,
                ),
            )

            second = init_onboarding_bundle(ctx, target)
            refreshed = plan_file.read_text(encoding="utf-8")

            self.assertIn("Custom note", refreshed)
            self.assertIn('amem plan-init "task" .', refreshed)
            self.assertNotIn("amem mcp-setup .", refreshed)
            self.assertIn("docs/plans/onboarding-mcp-config/plan.md", second.refreshed_files)

    def test_init_refactor_bundle_uses_first_hotspot_and_writes_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            ctx = self._build_context(root)
            for name in ["README.template.md", "spec.template.md", "plan.template.md", "task-graph.template.md", "validation.template.md"]:
                _write_text(root / "templates" / "planning" / name, f"# {name}\nplanning bundle\n## Acceptance Criteria\n## Change Set\n## Work Items\n## Exit Criteria\n## Required Checks\n{{{{TASK_NAME}}}}\n")
            _write_text(
                target / "service.py",
                "\n".join(
                    [
                        "def heavy(value):",
                        "    total = 0",
                        "    items = []",
                        "    results = {}",
                        "    status = None",
                        "    errors = []",
                        "    flags = set()",
                        "    cache = {}",
                        "    index = 0",
                        "    if value > 0:",
                        "        for outer in range(value):",
                        "            if outer % 2 == 0:",
                        "                for inner in range(3):",
                        "                    if inner == 1:",
                        "                        total += outer + inner",
                        "                        items.append(total)",
                        "                        results[outer] = inner",
                        "                        status = 'hot'",
                        "                    else:",
                        "                        errors.append(inner)",
                        "            else:",
                        "                while index < 2:",
                        "                    flags.add(index)",
                        "                    index += 1",
                        "    if total > 3:",
                        "        cache['total'] = total",
                        "    if items:",
                        "        return total + len(items) + len(results) + len(errors) + len(flags) + len(cache)",
                        "    return total",
                    ]
                )
                + "\n",
            )

            result = init_refactor_bundle(ctx, target)

            plan_dir = target / "docs" / "plans" / "refactor-service-py-heavy"
            self.assertEqual(result.task_slug, "refactor-service-py-heavy")
            self.assertTrue(result.hotspot_token.startswith("hotspot-"))
            self.assertTrue(plan_dir.exists())
            self.assertIn("service.py::heavy", (plan_dir / "README.md").read_text(encoding="utf-8"))
            self.assertIn(result.hotspot_token, (plan_dir / "README.md").read_text(encoding="utf-8"))
            self.assertIn("\"function_name\": \"heavy\"", (plan_dir / "spec.md").read_text(encoding="utf-8"))
            self.assertIn("\"rank_token\":", (plan_dir / "spec.md").read_text(encoding="utf-8"))
            self.assertIn("amem doctor .", (plan_dir / "validation.md").read_text(encoding="utf-8"))

    def test_cmd_refactor_bundle_returns_error_without_hotspot(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            ctx = self._build_context(root)
            for name in ["README.template.md", "spec.template.md", "plan.template.md", "task-graph.template.md", "validation.template.md"]:
                _write_text(root / "templates" / "planning" / name, f"# {name}\nplanning bundle\n{{{{TASK_NAME}}}}\n")
            _write_text(target / "service.py", "def clean(value):\n    return value + 1\n")

            exit_code = cmd_refactor_bundle(ctx, str(target))

            self.assertEqual(exit_code, 1)

    def test_cmd_plan_check_returns_zero_for_healthy_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            ctx = self._build_context(root)
            for name in ["README.template.md", "spec.template.md", "plan.template.md", "task-graph.template.md", "validation.template.md"]:
                _write_text(root / "templates" / "planning" / name, f"# {name}\nplanning bundle\n## Acceptance Criteria\n## Change Set\n## Work Items\n## Exit Criteria\n## Required Checks\n{{{{TASK_NAME}}}}\n")

            init_plan_bundle(ctx, "Healthy Bundle", target)

            exit_code = cmd_plan_check(ctx, str(target))

            self.assertEqual(exit_code, 0)
