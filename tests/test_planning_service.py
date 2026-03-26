from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from agents_memory.runtime import build_context
from agents_memory.services.planning import init_plan_bundle, slugify_task_name
from agents_memory.services.validation import cmd_plan_check, collect_plan_check_findings


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
            ctx = self._build_context(root)
            _write_text(bundle / "README.md", "# Demo\nplanning bundle\n")
            _write_text(bundle / "spec.md", "## Acceptance Criteria\n")
            _write_text(bundle / "plan.md", "## Change Set\n")
            _write_text(bundle / "validation.md", "## Required Checks\n")

            findings = collect_plan_check_findings(target, str(target))

            self.assertTrue(any(f.status == "FAIL" and f.key == "plan_files" for f in findings))

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
