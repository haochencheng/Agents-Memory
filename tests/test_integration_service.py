from __future__ import annotations

import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from agents_memory.runtime import build_context
from agents_memory.commands.integration import _parse_doctor_args, _parse_onboarding_execute_args
from agents_memory.services.integration import _doctor_action_sequence, _doctor_bootstrap_checklist, _doctor_bridge_check, _doctor_group_checks, _doctor_group_remediations, _doctor_group_status, _doctor_group_summary, _doctor_planning_checks, _doctor_overall, _doctor_runbook_steps, cmd_bridge_install, cmd_doctor, execute_onboarding_next_action, onboarding_next_action, write_vscode_mcp_json


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
        self.assertIn("amem doctor .", steps[0]["verify_with"])
        self.assertIn('amem plan-init "<task-name>" .', steps[0]["next_command"])
        self.assertIn("Done when", f"Done when: {steps[0]['done_when']}")
        self.assertFalse(steps[0]["safe_to_auto_execute"])
        self.assertTrue(steps[0]["approval_required"])
        self.assertEqual(steps[1]["group"], "Planning")
        self.assertIn('amem plan-init "<task-name>" .', steps[1]["command"])
        self.assertIn("amem doctor .", steps[1]["next_command"])

    def test_doctor_bootstrap_checklist_tracks_group_health(self) -> None:
        grouped_checks = [
            ("Core", [("OK", "registry", "registered")]),
            ("Planning", [("WARN", "planning_root", "missing docs/plans")]),
        ]
        runbook_steps = _doctor_runbook_steps(grouped_checks)
        checklist = _doctor_bootstrap_checklist(grouped_checks, runbook_steps)

        self.assertIn("[x] Core", checklist[0])
        self.assertIn("[ ] Planning", checklist[1])
        self.assertIn("[ ] Final verification", checklist[2])

    def test_onboarding_next_action_returns_pending_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_text(
                root / ".agents-memory" / "onboarding-state.json",
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
                                "done_when": "`amem doctor .` shows `[OK] mcp_config`.",
                                "next_command": "amem doctor .",
                                "safe_to_auto_execute": True,
                                "approval_required": False,
                                "approval_reason": "writes only local IDE config",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
            )

            action = onboarding_next_action(root)

            self.assertEqual(action["status"], "pending")
            self.assertEqual(action["command"], "amem mcp-setup .")
            self.assertTrue(action["blocking"])
            self.assertTrue(action["safe_to_auto_execute"])
            self.assertFalse(action["approval_required"])

    def test_parse_doctor_args_supports_export_flags(self) -> None:
        project_id_or_path, write_state, write_checklist = _parse_doctor_args(
            ["demo-project", "--write-state", "--write-checklist"]
        )

        self.assertEqual(project_id_or_path, "demo-project")
        self.assertTrue(write_state)
        self.assertTrue(write_checklist)

    def test_parse_onboarding_execute_args_supports_no_verify(self) -> None:
        project_id_or_path, verify, approve_unsafe = _parse_onboarding_execute_args(["demo-project", "--no-verify", "--approve-unsafe"])

        self.assertEqual(project_id_or_path, "demo-project")
        self.assertFalse(verify)
        self.assertTrue(approve_unsafe)

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
            self.assertIn("Verify with:", output)
            self.assertIn("Next command:", output)
            self.assertIn("Safe to auto execute:", output)
            self.assertIn("Approval required:", output)
            self.assertIn("Project Bootstrap Checklist:", output)
            self.assertIn("Integration:", output)
            self.assertIn("Optional:", output)
            self.assertIn("bridge not configured for this project", output)
            self.assertIn("bridge not configured; AGENTS read order check skipped", output)

    def test_cmd_doctor_can_export_artifacts(self) -> None:
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
                cmd_doctor(ctx, str(project_root), write_state=True, write_checklist=True)

            checklist_path = project_root / "docs" / "plans" / "bootstrap-checklist.md"
            state_path = project_root / ".agents-memory" / "onboarding-state.json"
            self.assertTrue(checklist_path.exists())
            self.assertTrue(state_path.exists())
            self.assertIn("# Bootstrap Checklist", checklist_path.read_text(encoding="utf-8"))
            self.assertIn('"project_id": "demo-project"', state_path.read_text(encoding="utf-8"))
            self.assertIn('"recommended_next_command": "amem mcp-setup ."', state_path.read_text(encoding="utf-8"))
            self.assertIn('"recommended_next_safe_to_auto_execute": true', state_path.read_text(encoding="utf-8"))
            self.assertIn("Exported Artifacts:", buffer.getvalue())

    def test_cmd_doctor_preserves_execution_metadata_when_rewriting_state(self) -> None:
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
            _write_text(
                project_root / ".agents-memory" / "onboarding-state.json",
                json.dumps(
                    {
                        "execution_history": [{"key": "mcp_config", "status": "verified"}],
                        "last_executed_action": {"key": "mcp_config", "status": "verified"},
                        "last_verified_action": {"key": "mcp_config", "status": "verified"},
                        "last_execution_status": "verified",
                        "last_execution_at": "2026-03-26T00:00:00+00:00",
                    },
                    ensure_ascii=False,
                ),
            )

            with redirect_stdout(StringIO()):
                cmd_doctor(ctx, str(project_root), write_state=True)

            state = json.loads((project_root / ".agents-memory" / "onboarding-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["execution_history"][0]["key"], "mcp_config")
            self.assertEqual(state["last_execution_status"], "verified")
            self.assertEqual(state["last_verified_action"]["key"], "mcp_config")

    def test_execute_onboarding_next_action_requires_approval_for_unsafe_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = self._build_context(root)
            project_root = root / "demo-project"
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
                                "key": "demo_step",
                                "priority": "required",
                                "detail": "seed a demo marker",
                                "command": "python3 -c \"from pathlib import Path; Path('.agents-memory/executed.txt').write_text('ok', encoding='utf-8')\"",
                                "verify_with": "python3 -c \"from pathlib import Path; raise SystemExit(0 if Path('.agents-memory/executed.txt').exists() else 1)\"",
                                "done_when": "marker file exists",
                                "next_command": "amem doctor .",
                                "safe_to_auto_execute": False,
                                "approval_required": True,
                                "approval_reason": "tracked file change needs human approval",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
            )

            result = execute_onboarding_next_action(ctx, project_root)

            self.assertEqual(result["status"], "approval_required")
            self.assertFalse((project_root / ".agents-memory" / "executed.txt").exists())
            self.assertFalse(result["state_updated"])
            self.assertIn("--approve-unsafe", result["recommended_command"])

    def test_execute_onboarding_next_action_records_execution_and_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = self._build_context(root)
            project_root = root / "demo-project"
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
                                "key": "demo_step",
                                "priority": "required",
                                "detail": "seed a demo marker",
                                "command": "python3 -c \"from pathlib import Path; Path('.agents-memory/executed.txt').write_text('ok', encoding='utf-8')\"",
                                "verify_with": "python3 -c \"from pathlib import Path; raise SystemExit(0 if Path('.agents-memory/executed.txt').exists() else 1)\"",
                                "done_when": "marker file exists",
                                "next_command": "amem doctor .",
                                "safe_to_auto_execute": False,
                                "approval_required": True,
                                "approval_reason": "tracked file change needs human approval",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
            )

            result = execute_onboarding_next_action(ctx, project_root, approve_unsafe=True)

            self.assertEqual(result["status"], "verified")
            self.assertTrue((project_root / ".agents-memory" / "executed.txt").exists())
            state = json.loads((project_root / ".agents-memory" / "onboarding-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["last_execution_status"], "verified")
            self.assertEqual(state["last_executed_action"]["key"], "demo_step")
            self.assertEqual(state["last_verified_action"]["key"], "demo_step")
            self.assertEqual(state["execution_history"][-1]["status"], "verified")
            self.assertTrue(state["last_executed_action"]["approve_unsafe"])
            self.assertTrue((project_root / "docs" / "plans" / "bootstrap-checklist.md").exists())
