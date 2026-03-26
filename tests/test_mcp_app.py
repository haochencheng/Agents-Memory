from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class MCPAppTests(unittest.TestCase):
    def _load_mcp_app(self, root: Path):
        previous_root = os.environ.get("AGENTS_MEMORY_ROOT")
        os.environ["AGENTS_MEMORY_ROOT"] = str(root)
        try:
            module = importlib.import_module("agents_memory.mcp_app")
            return importlib.reload(module)
        finally:
            if previous_root is None:
                os.environ.pop("AGENTS_MEMORY_ROOT", None)
            else:
                os.environ["AGENTS_MEMORY_ROOT"] = previous_root

    def test_memory_init_refactor_bundle_returns_bundle_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            _write_text(root / "templates" / "index.example.md", "index\n")
            _write_text(root / "templates" / "projects.example.md", "projects\n")
            _write_text(root / "templates" / "rules.example.md", "rules\n")
            for name in ["README.template.md", "spec.template.md", "plan.template.md", "task-graph.template.md", "validation.template.md"]:
                _write_text(
                    root / "templates" / "planning" / name,
                    f"# {name}\nplanning bundle\n## Acceptance Criteria\n## Change Set\n## Work Items\n## Exit Criteria\n## Required Checks\n{{{{TASK_NAME}}}}\n",
                )
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

            mcp_app = self._load_mcp_app(root)
            payload = json.loads(mcp_app.memory_init_refactor_bundle(str(target)))

            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["task_slug"], "refactor-service-py-heavy")
            self.assertEqual(payload["hotspot"]["function_name"], "heavy")
            self.assertTrue((target / "docs" / "plans" / "refactor-service-py-heavy").exists())
            self.assertIn("docs/plans/refactor-service-py-heavy/spec.md", payload["wrote_files"])
            state = json.loads((target / ".agents-memory" / "onboarding-state.json").read_text(encoding="utf-8"))
            self.assertTrue(state["project_bootstrap_ready"])
            self.assertTrue(state["project_bootstrap_complete"])
            self.assertEqual(state["recommended_steps"][0]["key"], "refactor_bundle")
            self.assertEqual(state["recommended_refactor_bundle"]["task_slug"], "refactor-service-py-heavy")
            self.assertEqual(payload["recommended_followup"]["bundle_path"], "docs/plans/refactor-service-py-heavy")

    def test_memory_get_refactor_hotspots_returns_structured_hotspots(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            _write_text(root / "templates" / "index.example.md", "index\n")
            _write_text(root / "templates" / "projects.example.md", "projects\n")
            _write_text(root / "templates" / "rules.example.md", "rules\n")
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

            mcp_app = self._load_mcp_app(root)
            payload = json.loads(mcp_app.memory_get_refactor_hotspots(str(target)))

            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["hotspot_count"], 1)
            self.assertEqual(payload["hotspots"][0]["function_name"], "heavy")
            self.assertEqual(payload["hotspots"][0]["relative_path"], "service.py")
            self.assertTrue(payload["hotspots"][0]["issues"])

    def test_memory_get_refactor_hotspots_returns_empty_list_when_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            _write_text(root / "templates" / "index.example.md", "index\n")
            _write_text(root / "templates" / "projects.example.md", "projects\n")
            _write_text(root / "templates" / "rules.example.md", "rules\n")
            _write_text(target / "service.py", "def clean(value):\n    return value + 1\n")

            mcp_app = self._load_mcp_app(root)
            payload = json.loads(mcp_app.memory_get_refactor_hotspots(str(target)))

            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["hotspot_count"], 0)
            self.assertEqual(payload["hotspots"], [])

    def test_memory_init_refactor_bundle_reports_missing_when_no_hotspot(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            _write_text(root / "templates" / "index.example.md", "index\n")
            _write_text(root / "templates" / "projects.example.md", "projects\n")
            _write_text(root / "templates" / "rules.example.md", "rules\n")
            for name in ["README.template.md", "spec.template.md", "plan.template.md", "task-graph.template.md", "validation.template.md"]:
                _write_text(root / "templates" / "planning" / name, f"# {name}\nplanning bundle\n{{{{TASK_NAME}}}}\n")
            _write_text(target / "service.py", "def clean(value):\n    return value + 1\n")

            mcp_app = self._load_mcp_app(root)
            payload = json.loads(mcp_app.memory_init_refactor_bundle(str(target)))

            self.assertEqual(payload["status"], "missing")
            self.assertIn("doctor . --write-checklist --write-state", payload["recommended_command"])


if __name__ == "__main__":
    unittest.main()
