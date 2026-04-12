from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from agents_memory.runtime import build_context
from agents_memory.services.records import collect_errors
from agents_memory.services.workflow_records import collect_workflow_records, migrate_legacy_workflow_records


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class WorkflowRecordMigrationTests(unittest.TestCase):
    def _build_context(self, root: Path):
        _write_text(root / "templates" / "index.example.md", "index\n")
        _write_text(root / "templates" / "projects.example.md", "# Projects\n")
        _write_text(root / "templates" / "rules.example.md", "# Rules\n")
        previous_root = os.environ.get("AGENTS_MEMORY_ROOT")
        os.environ["AGENTS_MEMORY_ROOT"] = str(root)
        try:
            return build_context(logger_name=f"tests.workflow.{root.name}", reference_file=__file__)
        finally:
            if previous_root is None:
                os.environ.pop("AGENTS_MEMORY_ROOT", None)
            else:
                os.environ["AGENTS_MEMORY_ROOT"] = previous_root

    def test_migrate_legacy_workflow_records_dry_run_does_not_move_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = self._build_context(root)
            _write_text(
                root / "errors" / "ERR-legacy-1.md",
                "---\nid: TASK-1\ntitle: Demo\nproject: Synapse-Network-Growing\nsource_type: task_completion\nstatus: completed\n---\n\nbody\n",
            )

            result = migrate_legacy_workflow_records(ctx, dry_run=True)

            self.assertEqual(result.migrated_count, 1)
            self.assertTrue((root / "errors" / "ERR-legacy-1.md").exists())
            self.assertFalse((root / "memory" / "workflow_records" / "TASK-1.md").exists())

    def test_migrate_legacy_workflow_records_moves_workflow_entries_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = self._build_context(root)
            _write_text(
                root / "errors" / "ERR-legacy-task.md",
                "---\nid: TASK-7\ntitle: Review output\nproject: Synapse-Network-Growing\nsource_type: task_completion\nstatus: completed\ncreated_at: 2026-04-12T10:00:00Z\n---\n\nworkflow body\n",
            )
            _write_text(
                root / "errors" / "ERR-real-error.md",
                "---\nid: ERR-20260412-001\ntitle: Failure\nproject: Synapse-Network-Growing\nsource_type: error_record\nstatus: new\ndate: 2026-04-12\n---\n\nerror body\n",
            )

            result = migrate_legacy_workflow_records(ctx)

            self.assertEqual(result.migrated_count, 1)
            self.assertFalse((root / "errors" / "ERR-legacy-task.md").exists())
            self.assertTrue((root / "memory" / "workflow_records" / "TASK-7.md").exists())
            self.assertTrue((root / "errors" / "ERR-real-error.md").exists())

            errors = collect_errors(ctx)
            self.assertEqual([item["id"] for item in errors], ["ERR-20260412-001"])
            workflow = collect_workflow_records(ctx)
            self.assertEqual([item["id"] for item in workflow], ["TASK-7"])
            self.assertEqual(workflow[0]["project"], "synapse-network-growing")

    def test_migrate_legacy_workflow_records_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = self._build_context(root)
            _write_text(
                root / "errors" / "ERR-legacy-req.md",
                "---\nid: REQ-1\ntitle: Launch readiness\nproject: Synapse-Network\nsource_type: requirement_completion\nstatus: completed\n---\n\nbody\n",
            )

            first = migrate_legacy_workflow_records(ctx)
            second = migrate_legacy_workflow_records(ctx)

            self.assertEqual(first.migrated_count, 1)
            self.assertEqual(second.migrated_count, 0)
            self.assertTrue((root / "memory" / "workflow_records" / "REQ-1.md").exists())


if __name__ == "__main__":
    unittest.main()
