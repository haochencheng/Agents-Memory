from __future__ import annotations

import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from agents_memory.runtime import build_context
from agents_memory.commands.integration import _parse_doctor_args, _parse_enable_args, _parse_onboarding_execute_args
from agents_memory.services.integration import _doctor_action_sequence, _doctor_bootstrap_checklist, _doctor_bridge_check, _doctor_group_checks, _doctor_group_remediations, _doctor_group_status, _doctor_group_summary, _doctor_planning_checks, _doctor_refactor_watch_checks, _doctor_overall, _doctor_runbook_steps, cmd_bridge_install, cmd_doctor, cmd_enable, execute_onboarding_next_action, onboarding_next_action, write_vscode_mcp_json


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

    def test_doctor_refactor_watch_checks_flag_complex_function(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project_root = root / "demo-project"
            project_root.mkdir()
            _write_text(
                project_root / "service.py",
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

            checks = _doctor_refactor_watch_checks(project_root)

            self.assertTrue(any(status == "WARN" and key == "refactor_watch" for status, key, _detail in checks))
            self.assertTrue(any("service.py::heavy" in detail for _status, _key, detail in checks))

    def test_doctor_overall_ignores_info_only_noise(self) -> None:
        overall = _doctor_overall(
            [
                ("OK", "registry", "registered"),
                ("OK", "root", "/tmp/demo-project"),
                ("INFO", "bridge_instruction", "bridge not configured for this project"),
                ("INFO", "profile_manifest", "no applied profile manifest found"),
                ("WARN", "refactor_watch", "service.py::heavy high complexity"),
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

    def test_onboarding_next_action_returns_recommended_refactor_followup_when_bootstrap_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_text(
                root / ".agents-memory" / "onboarding-state.json",
                json.dumps(
                    {
                        "project_bootstrap_ready": True,
                        "project_bootstrap_complete": True,
                        "runbook_steps": [],
                        "recommended_steps": [
                            {
                                "group": "Refactor",
                                "key": "refactor_bundle",
                                "priority": "recommended",
                                "command": "python3 scripts/memory.py refactor-bundle . --token hotspot-demo-token",
                                "verify_with": "amem doctor .",
                                "done_when": "doctor no longer reports the hotspot",
                                "next_command": "amem doctor .",
                                "safe_to_auto_execute": True,
                                "approval_required": False,
                                "approval_reason": "refreshes generated planning docs only",
                                "bundle_path": "docs/plans/refactor-service-py-heavy",
                                "hotspot": {"identifier": "service.py::heavy", "rank_token": "hotspot-demo-token"},
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
            )

            action = onboarding_next_action(root)

            self.assertEqual(action["status"], "pending")
            self.assertEqual(action["step_source"], "recommended")
            self.assertFalse(action["blocking"])
            self.assertEqual(action["bundle_path"], "docs/plans/refactor-service-py-heavy")
            self.assertEqual(action["hotspot"]["identifier"], "service.py::heavy")

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

    def test_parse_enable_args_supports_full_mode(self) -> None:
        project_id_or_path, full, dry_run = _parse_enable_args(["demo-project", "--full"])

        self.assertEqual(project_id_or_path, "demo-project")
        self.assertTrue(full)
        self.assertFalse(dry_run)

    def test_parse_enable_args_supports_dry_run(self) -> None:
        project_id_or_path, full, dry_run = _parse_enable_args(["demo-project", "--dry-run"])

        self.assertEqual(project_id_or_path, "demo-project")
        self.assertFalse(full)
        self.assertTrue(dry_run)

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
            refactor_watch_path = project_root / "docs" / "plans" / "refactor-watch.md"
            state_path = project_root / ".agents-memory" / "onboarding-state.json"
            self.assertTrue(checklist_path.exists())
            self.assertTrue(refactor_watch_path.exists())
            self.assertTrue(state_path.exists())
            self.assertIn("# Bootstrap Checklist", checklist_path.read_text(encoding="utf-8"))
            self.assertIn("# Refactor Watch", refactor_watch_path.read_text(encoding="utf-8"))
            self.assertIn("amem refactor-bundle .", refactor_watch_path.read_text(encoding="utf-8"))
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

    def test_cmd_doctor_preserves_live_refactor_followup_metadata_when_rewriting_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = self._build_context(root)
            project_root = root / "demo-project"
            project_root.mkdir()
            _write_text(
                project_root / "service.py",
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
                        "recommended_steps": [
                            {
                                "group": "Refactor",
                                "key": "refactor_bundle",
                                "bundle_path": "docs/plans/refactor-demo",
                                "hotspot": {"identifier": "service.py::heavy"},
                            }
                        ],
                        "recommended_refactor_bundle": {
                            "bundle_path": "docs/plans/refactor-demo",
                            "task_slug": "refactor-demo",
                            "hotspot": {"identifier": "service.py::heavy"},
                        },
                    },
                    ensure_ascii=False,
                ),
            )

            with redirect_stdout(StringIO()):
                cmd_doctor(ctx, str(project_root), write_state=True)

            state = json.loads((project_root / ".agents-memory" / "onboarding-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["recommended_steps"][0]["key"], "refactor_bundle")
            self.assertEqual(state["recommended_refactor_bundle"]["task_slug"], "refactor-demo")

    def test_cmd_doctor_clears_stale_refactor_followup_metadata_when_rewriting_state(self) -> None:
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
                        "recommended_steps": [
                            {
                                "group": "Refactor",
                                "key": "refactor_bundle",
                                "bundle_path": "docs/plans/refactor-demo",
                                "hotspot": {"identifier": "service.py::heavy"},
                            }
                        ],
                        "recommended_refactor_bundle": {
                            "bundle_path": "docs/plans/refactor-demo",
                            "task_slug": "refactor-demo",
                            "hotspot": {"identifier": "service.py::heavy"},
                        },
                    },
                    ensure_ascii=False,
                ),
            )

            with redirect_stdout(StringIO()):
                cmd_doctor(ctx, str(project_root), write_state=True)

            state = json.loads((project_root / ".agents-memory" / "onboarding-state.json").read_text(encoding="utf-8"))
            self.assertNotIn("recommended_steps", state)
            self.assertNotIn("recommended_refactor_bundle", state)
            self.assertNotEqual(state["recommended_next_key"], "refactor_bundle")

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

    def test_cmd_enable_default_mode_bootstraps_project_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = self._build_context(root)
            project_root = root / "demo-project"
            project_root.mkdir()
            _write_text(root / "templates" / "agents-memory-bridge.instructions.md", "root={{AGENTS_MEMORY_ROOT}}\nproject={{PROJECT_ID}}\n")
            _write_text(root / "templates" / "agents-memory-copilot-instructions.md", "copilot {{PROJECT_ID}} {{AGENTS_MEMORY_ROOT}}\n")
            for name in ["README.template.md", "spec.template.md", "plan.template.md", "task-graph.template.md", "validation.template.md"]:
                _write_text(root / "templates" / "planning" / name, f"# {name}\nplanning bundle\n## Acceptance Criteria\n## Change Set\n## Work Items\n## Exit Criteria\n## Required Checks\n{{{{TASK_NAME}}}}\n")

            with redirect_stdout(StringIO()):
                exit_code = cmd_enable(ctx, str(project_root))

            self.assertEqual(exit_code, 0)
            self.assertIn("## demo-project", (root / "memory" / "projects.md").read_text(encoding="utf-8"))
            self.assertTrue((project_root / ".github" / "instructions" / "agents-memory-bridge.instructions.md").exists())
            self.assertTrue((project_root / ".vscode" / "mcp.json").exists())
            self.assertTrue((project_root / ".agents-memory" / "onboarding-state.json").exists())
            self.assertTrue((project_root / "docs" / "plans" / "bootstrap-checklist.md").exists())
            self.assertTrue(any(path.is_dir() for path in (project_root / "docs" / "plans").glob("onboarding-*")))

    def test_cmd_enable_dry_run_does_not_write_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = self._build_context(root)
            project_root = root / "demo-project"
            project_root.mkdir()
            _write_text(root / "templates" / "agents-memory-bridge.instructions.md", "root={{AGENTS_MEMORY_ROOT}}\nproject={{PROJECT_ID}}\n")
            _write_text(root / "templates" / "agents-memory-copilot-instructions.md", "copilot {{PROJECT_ID}} {{AGENTS_MEMORY_ROOT}}\n")
            for name in ["README.template.md", "spec.template.md", "plan.template.md", "task-graph.template.md", "validation.template.md"]:
                _write_text(root / "templates" / "planning" / name, f"# {name}\nplanning bundle\n## Acceptance Criteria\n## Change Set\n## Work Items\n## Exit Criteria\n## Required Checks\n{{{{TASK_NAME}}}}\n")

            buffer = StringIO()
            with redirect_stdout(buffer):
                exit_code = cmd_enable(ctx, str(project_root), dry_run=True)

            self.assertEqual(exit_code, 0)
            self.assertIn("Planned Actions:", buffer.getvalue())
            self.assertIn("Planned Writes:", buffer.getvalue())
            projects_file = root / "memory" / "projects.md"
            if projects_file.exists():
                self.assertNotIn("## demo-project", projects_file.read_text(encoding="utf-8"))
            self.assertFalse((project_root / ".vscode" / "mcp.json").exists())
            self.assertFalse((project_root / ".agents-memory" / "onboarding-state.json").exists())
            self.assertFalse((project_root / "docs" / "plans").exists())

    def test_cmd_enable_full_mode_applies_profile_and_refactor_followup(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = self._build_context(root)
            project_root = root / "demo-project"
            project_root.mkdir()
            _write_text(root / "templates" / "agents-memory-bridge.instructions.md", "root={{AGENTS_MEMORY_ROOT}}\nproject={{PROJECT_ID}}\n")
            _write_text(root / "templates" / "agents-memory-copilot-instructions.md", "<!-- AGENTS-MEMORY:START -->\nproject={{PROJECT_ID}}\nroot={{AGENTS_MEMORY_ROOT}}\n<!-- AGENTS-MEMORY:END -->\n")
            for name in ["README.template.md", "spec.template.md", "plan.template.md", "task-graph.template.md", "validation.template.md"]:
                _write_text(root / "templates" / "planning" / name, f"# {name}\nplanning bundle\n## Acceptance Criteria\n## Change Set\n## Work Items\n## Exit Criteria\n## Required Checks\n{{{{TASK_NAME}}}}\n")
            _write_text(
                root / "profiles" / "python-service.yaml",
                json.dumps(
                    {
                        "id": "python-service",
                        "display_name": "Python Service",
                        "applies_to": ["backend", "python"],
                        "standards": ["standards/docs/docs-sync.instructions.md"],
                        "templates": ["templates/profile/python-service/docs/plans/README.example.md"],
                        "commands": {"doctor": "amem doctor ."},
                        "bootstrap": {"create": [".github/instructions/", "docs/", "tests/"]},
                    },
                    ensure_ascii=False,
                ),
            )
            _write_text(root / "standards" / "docs" / "docs-sync.instructions.md", "docs sync\n")
            _write_text(root / "templates" / "profile" / "python-service" / "docs" / "plans" / "README.example.md", "planning root\n")
            _write_text(project_root / "pyproject.toml", "[project]\nname='demo'\n")
            _write_text(
                project_root / "service.py",
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

            with redirect_stdout(StringIO()):
                exit_code = cmd_enable(ctx, str(project_root), full=True)

            self.assertEqual(exit_code, 0)
            self.assertTrue((project_root / ".github" / "copilot-instructions.md").exists())
            self.assertTrue((project_root / ".github" / "instructions" / "agents-memory" / "profile-manifest.json").exists())
            self.assertTrue(any(path.is_dir() for path in (project_root / "docs" / "plans").glob("refactor-*")))
            state = json.loads((project_root / ".agents-memory" / "onboarding-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["recommended_steps"][0]["key"], "refactor_bundle")
            self.assertIn("--token hotspot-", state["recommended_steps"][0]["command"])
            self.assertTrue(state["recommended_refactor_bundle"]["hotspot_token"].startswith("hotspot-"))
