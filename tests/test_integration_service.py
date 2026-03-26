from __future__ import annotations

import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from agents_memory.runtime import build_context
from agents_memory.services.integration import _doctor_action_sequence, _doctor_bridge_check, _doctor_group_checks, _doctor_group_remediations, _doctor_group_status, _doctor_group_summary, _doctor_planning_checks, _doctor_overall, _doctor_runbook_steps, cmd_bridge_install, cmd_doctor, write_vscode_mcp_json


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class IntegrationServiceTests(unittest.TestCase):
    def _build_context(self, root: Path):
        _write_text(root / "templates" / "index.example.md", "index\n")
        _write_text(root / "templates" / "projects.example.md", "# Project Registry\n")
        _write_text(root / "templates" / "rules.example.md", "# Promoted Rules\n")
        previous_root = os.environ.get("AGENTS_MEMORY_ROOT")
        os.environ["AGENTS_MEMORY_ROOT"] = str(root)
        try:
            return build_context(logger_name=f"tests.integration.{root.name}", reference_file=__file__)
        finally:
            if previous_root is None:
                os.environ.pop("AGENTS_MEMORY_ROOT", None)
            else:
                os.environ["AGENTS_MEMORY_ROOT"] = previous_root

    def test_write_vscode_mcp_json_merges_existing_servers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = self._build_context(root)
            project_root = root / "demo-project"
            project_root.mkdir()
            mcp_path = project_root / ".vscode" / "mcp.json"
            _write_text(
                mcp_path,
                json.dumps(
                    {
                        "servers": {
                            "existing-server": {
                                "type": "stdio",
                                "command": "python3",
                                "args": ["existing.py"],
                                "env": {},
                            }
                        }
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
            )

            changed = write_vscode_mcp_json(ctx, project_root)
            content = json.loads(mcp_path.read_text(encoding="utf-8"))

            self.assertTrue(changed)
            self.assertIn("existing-server", content["servers"])
            self.assertIn("agents-memory", content["servers"])
            self.assertIn(str(ctx.base_dir / "scripts" / "mcp_server.py"), content["servers"]["agents-memory"]["args"])

    def test_write_vscode_mcp_json_skips_when_agents_memory_already_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = self._build_context(root)
            project_root = root / "demo-project"
            project_root.mkdir()
            mcp_path = project_root / ".vscode" / "mcp.json"
            _write_text(
                mcp_path,
                json.dumps(
                    {
                        "servers": {
                            "agents-memory": {
                                "type": "stdio",
                                "command": "python3.12",
                                "args": [str(ctx.base_dir / "scripts" / "mcp_server.py")],
                                "env": {},
                            }
                        }
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
            )

            changed = write_vscode_mcp_json(ctx, project_root)

            self.assertFalse(changed)

    def test_cmd_bridge_install_renders_repo_specific_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = self._build_context(root)
            project_root = root / "demo-project"
            project_root.mkdir()
            _write_text(
                root / "templates" / "agents-memory-bridge.instructions.md",
                "root={{AGENTS_MEMORY_ROOT}}\nproject={{PROJECT_ID}}\n",
            )
            _write_text(
                root / "memory" / "projects.md",
                "\n".join(
                    [
                        "# Project Registry",
                        "",
                        "## demo-project",
                        f"- **id**: demo-project",
                        f"- **root**: {project_root}",
                        "- **bridge_instruction**: .github/instructions/agents-memory-bridge.instructions.md",
                        "- **active**: true",
                    ]
                ),
            )

            cmd_bridge_install(ctx, "demo-project")

            installed = project_root / ".github" / "instructions" / "agents-memory-bridge.instructions.md"
            self.assertTrue(installed.exists())
            content = installed.read_text(encoding="utf-8")
            self.assertIn(f"root={ctx.base_dir}", content)
            self.assertIn("project=demo-project", content)

    def test_doctor_planning_checks_reports_ok_when_bundle_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project_root = root / "demo-project"
            bundle = project_root / "docs" / "plans" / "demo-task"
            bundle.mkdir(parents=True)
            self._build_context(root)
            for filename, content in {
                "README.md": "planning bundle\n",
                "spec.md": "## Acceptance Criteria\n",
                "plan.md": "## Change Set\n",
                "task-graph.md": "## Work Items\n## Exit Criteria\n",
                "validation.md": "## Required Checks\n",
            }.items():
                _write_text(bundle / filename, content)

            checks = _doctor_planning_checks(project_root)

            self.assertTrue(any(check[0] == "OK" and check[1] == "planning_bundle" for check in checks))

    def test_doctor_bridge_check_treats_missing_bridge_as_info(self) -> None:
        status, key, detail = _doctor_bridge_check(Path("/tmp/demo-project"), None)

        self.assertEqual((status, key), ("INFO", "bridge_instruction"))
        self.assertIn("bridge not configured", detail)

    def test_doctor_overall_ignores_info_only_noise(self) -> None:
        overall = _doctor_overall(
            [
                ("OK", "registry", "registered"),
                ("OK", "root", "/tmp/demo-project"),
                ("INFO", "bridge_instruction", "bridge not configured for this project"),
                ("INFO", "profile_manifest", "no applied profile manifest found"),
            ]
        )

        self.assertEqual(overall, "READY")

    def test_doctor_group_checks_splits_sections(self) -> None:
        groups = _doctor_group_checks(
            [
                ("OK", "registry", "registered"),
                ("OK", "planning_bundle", "bundle ok"),
                ("OK", "mcp_config", "configured"),
                ("WARN", "copilot_activation", "missing"),
            ]
        )

        self.assertEqual([name for name, _items in groups], ["Core", "Planning", "Integration", "Optional"])

    def test_doctor_group_summary_and_remediation(self) -> None:
        group_checks = [
            ("OK", "mcp_config", "configured"),
            ("WARN", "bridge_instruction", "missing bridge"),
        ]

        self.assertEqual(_doctor_group_status(group_checks), "WATCH")
        self.assertIn("warn=1", _doctor_group_summary("Integration", group_checks))
        self.assertTrue(_doctor_group_remediations("Integration", group_checks))

    def test_doctor_action_sequence_prioritizes_group_order(self) -> None:
        action_sequence = _doctor_action_sequence(
            [
                ("Core", [("WARN", "registry", "not registered")]),
                ("Planning", [("WARN", "planning_root", "missing docs/plans")]),
                ("Integration", [("WARN", "mcp_config", "missing config")]),
                ("Optional", [("WARN", "copilot_activation", "missing activation")]),
            ]
        )

        self.assertEqual(len(action_sequence), 4)
        self.assertTrue(action_sequence[0].startswith("Core (required):"))
        self.assertTrue(action_sequence[1].startswith("Planning (required):"))
        self.assertTrue(action_sequence[2].startswith("Integration (required):"))
        self.assertTrue(action_sequence[3].startswith("Optional (recommended):"))

    def test_doctor_runbook_steps_include_command_and_done_when(self) -> None:
        steps = _doctor_runbook_steps(
            [
                ("Core", [("WARN", "registry", "not registered")]),
                ("Planning", [("WARN", "planning_root", "missing docs/plans")]),
            ]
        )

        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0]["group"], "Core")
        self.assertEqual(steps[0]["key"], "registry")
        self.assertIn("amem register .", steps[0]["command"])
        self.assertIn("Done when", f"Done when: {steps[0]['done_when']}")
        self.assertEqual(steps[1]["group"], "Planning")
        self.assertIn('amem plan-init "<task-name>" .', steps[1]["command"])

    def test_cmd_doctor_surfaces_planning_root_warning_for_applied_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = self._build_context(root)
            project_root = root / "demo-project"
            project_root.mkdir()
            _write_text(
                root / "memory" / "projects.md",
                "\n".join(
                    [
                        "# Project Registry",
                        "",
                        "## demo-project",
                        "- **id**: demo-project",
                        f"- **root**: {project_root}",
                        "- **bridge_instruction**: .github/instructions/agents-memory-bridge.instructions.md",
                        "- **active**: true",
                    ]
                ),
            )
            _write_text(
                project_root / ".github" / "instructions" / "agents-memory" / "profile-manifest.json",
                json.dumps({"profile_id": "python-service"}, ensure_ascii=False),
            )
            _write_text(
                root / "profiles" / "python-service.yaml",
                '{"id":"python-service","display_name":"Python Service","applies_to":["backend"],"standards":[],"templates":[],"commands":{},"bootstrap":{"create":[]}}\n',
            )

            buffer = StringIO()
            with redirect_stdout(buffer):
                cmd_doctor(ctx, str(project_root))

            self.assertIn("planning_root", buffer.getvalue())

    def test_cmd_doctor_skips_bridge_noise_when_registry_disables_bridge(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = self._build_context(root)
            project_root = root / "demo-project"
            project_root.mkdir()
            _write_text(
                root / "memory" / "projects.md",
                "\n".join(
                    [
                        "# Project Registry",
                        "",
                        "## demo-project",
                        "- **id**: demo-project",
                        f"- **root**: {project_root}",
                        '- **bridge_instruction**: ""',
                        "- **active**: true",
                    ]
                ),
            )

            buffer = StringIO()
            with redirect_stdout(buffer):
                cmd_doctor(ctx, str(project_root))

            output = buffer.getvalue()
            self.assertIn("Core:", output)
            self.assertIn("Summary:", output)
            self.assertIn("Action Sequence:", output)
            self.assertIn("Onboarding Runbook:", output)
            self.assertIn("Integration:", output)
            self.assertIn("Optional:", output)
            self.assertIn("bridge not configured for this project", output)
            self.assertIn("bridge not configured; AGENTS read order check skipped", output)
