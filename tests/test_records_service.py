from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from agents_memory.runtime import build_context
from agents_memory.services.records import cmd_update_index, collect_errors, dedupe_error_records, find_error_record, total_error_count


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class RecordsServiceTests(unittest.TestCase):
    def _build_context(self, root: Path):
        _write_text(root / "templates" / "index.example.md", "index\n")
        _write_text(root / "templates" / "projects.example.md", "# Project Registry\n")
        _write_text(root / "templates" / "rules.example.md", "# Promoted Rules\n")
        previous_root = os.environ.get("AGENTS_MEMORY_ROOT")
        os.environ["AGENTS_MEMORY_ROOT"] = str(root)
        try:
            return build_context(logger_name=f"tests.records.{root.name}", reference_file=__file__)
        finally:
            if previous_root is None:
                os.environ.pop("AGENTS_MEMORY_ROOT", None)
            else:
                os.environ["AGENTS_MEMORY_ROOT"] = previous_root

    def test_collect_errors_filters_by_status_and_update_index_summarizes_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = self._build_context(root)
            _write_text(
                ctx.errors_dir / "2026-03-26-other-001.md",
                """---
id: 2026-03-26-other-001
date: 2026-03-26
project: other
domain: python
category: build-error
severity: warning
status: new
promoted_to: ""
repeat_count: 1
tags: []
---

## 提炼规则

rule one
""",
            )
            _write_text(
                ctx.errors_dir / "2026-03-26-other-002.md",
                """---
id: 2026-03-26-other-002
date: 2026-03-26
project: other
domain: python
category: logic-error
severity: info
status: promoted
promoted_to: ".github/instructions/python.instructions.md"
repeat_count: 2
tags: []
---

## 提炼规则

rule two
""",
            )

            active = collect_errors(ctx, status_filter=["new", "reviewed"])
            promoted = collect_errors(ctx, status_filter=["promoted"])
            cmd_update_index(ctx)
            index_content = ctx.index_file.read_text(encoding="utf-8")

            self.assertEqual(len(active), 1)
            self.assertEqual(len(promoted), 1)
            self.assertEqual(total_error_count(ctx), 2)
            self.assertIn("| 错误模式 (errors) | 2 | `errors/` |", index_content)
            self.assertIn("2026-03-26-other-002", index_content)
            self.assertIn("`build-error`", index_content)

    def test_dedupe_error_records_keeps_latest_duplicate_per_project_and_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = self._build_context(root)
            _write_text(
                ctx.errors_dir / "ERR-20260411-001.md",
                """---
id: TASK-24-FAIL
date: 2026-04-11
project: synapse-network-growing
title: repeated failure
source_type: error_record
status: new
---

older
""",
            )
            _write_text(
                ctx.errors_dir / "ERR-20260412-002.md",
                """---
id: TASK-24-FAIL
date: 2026-04-12
project: synapse-network-growing
title: repeated failure
source_type: error_record
status: new
---

newer
""",
            )

            deduped = dedupe_error_records(collect_errors(ctx))

            self.assertEqual(len(deduped), 1)
            self.assertEqual(deduped[0]["id"], "TASK-24-FAIL")
            self.assertTrue(deduped[0]["_file"].endswith("ERR-20260412-002.md"))

    def test_find_error_record_matches_frontmatter_id_when_filename_differs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = self._build_context(root)
            _write_text(
                ctx.errors_dir / "ERR-20260411-044.md",
                """---
id: TASK-24-FAIL
date: 2026-04-11
project: synapse-network-growing
title: repeated failure
source_type: error_record
status: new
---

body
""",
            )

            record = find_error_record(ctx, "TASK-24-FAIL")

            self.assertIsNotNone(record)
            assert record is not None
            self.assertTrue(record["_file"].endswith("ERR-20260411-044.md"))
