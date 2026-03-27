from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from agents_memory.runtime import build_context
from agents_memory.services.profiles import PROFILE_MANIFEST_REL, PROJECT_FACTS_REL, apply_profile, list_profiles, load_profile, render_profile_overlays, sync_profile_standards
from agents_memory.services.validation import collect_profile_check_findings


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class ProfilesServiceTests(unittest.TestCase):
    def _build_context(self, root: Path):
        _write_text(root / "templates" / "index.example.md", "index\n")
        _write_text(root / "templates" / "projects.example.md", "# Project Registry\n")
        _write_text(root / "templates" / "rules.example.md", "# Promoted Rules\n")
        previous_root = os.environ.get("AGENTS_MEMORY_ROOT")
        os.environ["AGENTS_MEMORY_ROOT"] = str(root)
        try:
            return build_context(logger_name=f"tests.profiles.{root.name}", reference_file=__file__)
        finally:
            if previous_root is None:
                os.environ.pop("AGENTS_MEMORY_ROOT", None)
            else:
                os.environ["AGENTS_MEMORY_ROOT"] = previous_root

    def test_list_profiles_returns_seed_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = self._build_context(root)
            _write_text(
                root / "profiles" / "python-service.yaml",
                '{"id":"python-service","display_name":"Python Service","applies_to":["backend"],"standards":[],"templates":[],"commands":{},"bootstrap":{"create":[]}}\n',
            )
            _write_text(
                root / "profiles" / "frontend-app.yaml",
                '{"id":"frontend-app","display_name":"Frontend App","applies_to":["frontend"],"standards":[],"templates":[],"commands":{},"bootstrap":{"create":[]}}\n',
            )

            profiles = list_profiles(ctx)

            self.assertEqual([profile.id for profile in profiles], ["frontend-app", "python-service"])

    def test_load_profile_reads_json_subset_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = self._build_context(root)
            _write_text(
                root / "profiles" / "python-service.yaml",
                '{"id":"python-service","display_name":"Python Service","applies_to":["backend","fastapi"],"standards":["standards/python/base.instructions.md"],"templates":["templates/profile/python-service/AGENTS.example.md"],"variables":[{"name":"python_bin","description":"Python executable","default":"python3","required":false}],"detectors":[{"id":"python_project","kind":"path_exists","output":"language.python","config":{"any_of":["pyproject.toml"]}}],"overlays":[{"target":".github/instructions/agents-memory/project-local.instructions.md","template":"templates/profile/python-service/project-local.instructions.example.md","variables":["python_bin"],"detectors":["python_project"],"managed_by":"profile-render"}],"commands":{"docs_check":"amem docs-check"},"bootstrap":{"create":["docs/"]}}\n',
            )
            _write_text(root / "templates" / "profile" / "python-service" / "project-local.instructions.example.md", "python={{variable.python_bin}}\nactive={{fact.language.python}}\n")

            profile = load_profile(ctx, "python-service")

            self.assertEqual(profile.display_name, "Python Service")
            self.assertEqual(profile.applies_to, ["backend", "fastapi"])
            self.assertEqual(profile.bootstrap_create, ["docs/"])
            self.assertEqual(profile.variables[0].name, "python_bin")
            self.assertEqual(profile.detectors[0].output, "language.python")
            self.assertEqual(profile.overlays[0].managed_by, "profile-render")

    def test_load_profile_defaults_new_schema_fields_to_empty_lists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = self._build_context(root)
            _write_text(
                root / "profiles" / "python-service.yaml",
                '{"id":"python-service","display_name":"Python Service","applies_to":["backend"],"standards":[],"templates":[],"commands":{},"bootstrap":{"create":[]}}\n',
            )

            profile = load_profile(ctx, "python-service")

            self.assertEqual(profile.variables, [])
            self.assertEqual(profile.detectors, [])
            self.assertEqual(profile.overlays, [])

    def test_agent_runtime_profile_includes_python_baseline(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        previous_root = os.environ.get("AGENTS_MEMORY_ROOT")
        os.environ["AGENTS_MEMORY_ROOT"] = str(repo_root)
        try:
            ctx = build_context(logger_name="tests.profiles.agent_runtime", reference_file=__file__)
            profile = load_profile(ctx, "agent-runtime")
        finally:
            if previous_root is None:
                os.environ.pop("AGENTS_MEMORY_ROOT", None)
            else:
                os.environ["AGENTS_MEMORY_ROOT"] = previous_root

        self.assertIn("standards/python/base.instructions.md", profile.standards)
        self.assertTrue(profile.variables)
        self.assertTrue(profile.detectors)

    def test_built_in_profiles_use_extended_detector_kinds(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        previous_root = os.environ.get("AGENTS_MEMORY_ROOT")
        os.environ["AGENTS_MEMORY_ROOT"] = str(repo_root)
        try:
            ctx = build_context(logger_name="tests.profiles.builtins", reference_file=__file__)
            python_profile = load_profile(ctx, "python-service")
            frontend_profile = load_profile(ctx, "frontend-app")
            fullstack_profile = load_profile(ctx, "fullstack-product")
        finally:
            if previous_root is None:
                os.environ.pop("AGENTS_MEMORY_ROOT", None)
            else:
                os.environ["AGENTS_MEMORY_ROOT"] = previous_root

        self.assertIn("file_contains", {item.kind for item in python_profile.detectors})
        self.assertIn("json_key_exists", {item.kind for item in frontend_profile.detectors})
        self.assertIn("file_contains", {item.kind for item in frontend_profile.detectors})
        self.assertIn("json_key_exists", {item.kind for item in fullstack_profile.detectors})
        self.assertIn("file_contains", {item.kind for item in fullstack_profile.detectors})

    def test_apply_profile_creates_dirs_and_installs_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            ctx = self._build_context(root)
            _write_text(
                root / "profiles" / "python-service.yaml",
                '{"id":"python-service","display_name":"Python Service","applies_to":["backend"],"standards":["standards/python/base.instructions.md"],"templates":["templates/profile/python-service/AGENTS.example.md","templates/profile/python-service/docs/plans/README.example.md"],"commands":{"docs_check":"amem docs-check","doctor":"amem doctor"},"bootstrap":{"create":["docs/","tests/"]}}\n',
            )
            _write_text(root / "standards" / "python" / "base.instructions.md", "# Python Base\n")
            _write_text(root / "templates" / "profile" / "python-service" / "AGENTS.example.md", "# Target AGENTS\n")
            _write_text(root / "templates" / "profile" / "python-service" / "docs" / "plans" / "README.example.md", "# Planning Bundles\n")

            result = apply_profile(ctx, load_profile(ctx, "python-service"), target)

            self.assertTrue((target / "docs").exists())
            self.assertTrue((target / "tests").exists())
            self.assertTrue((target / ".github" / "instructions" / "agents-memory" / "standards" / "python" / "base.instructions.md").exists())
            self.assertTrue((target / "AGENTS.md").exists())
            self.assertTrue((target / "docs" / "plans" / "README.md").exists())
            self.assertTrue((target / PROFILE_MANIFEST_REL).exists())
            self.assertTrue((target / PROJECT_FACTS_REL).exists())
            self.assertEqual(len(result.installed_standards), 1)
            self.assertEqual(len(result.wrote_templates), 2)

    def test_apply_profile_writes_extended_schema_to_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            ctx = self._build_context(root)
            _write_text(
                root / "profiles" / "python-service.yaml",
                '{"id":"python-service","display_name":"Python Service","applies_to":["backend"],"standards":[],"templates":[],"variables":[{"name":"python_bin","description":"Python executable","default":"python3","required":false}],"detectors":[{"id":"python_project","kind":"path_exists","output":"language.python","config":{"any_of":["pyproject.toml"]}}],"overlays":[{"target":".github/instructions/agents-memory/project-local.instructions.md","template":"templates/profile/python-service/project-local.instructions.example.md","variables":["python_bin"],"detectors":["python_project"],"managed_by":"profile-render"}],"commands":{},"bootstrap":{"create":[]}}\n',
            )
            _write_text(root / "templates" / "profile" / "python-service" / "project-local.instructions.example.md", "python={{variable.python_bin}}\n")

            apply_profile(ctx, load_profile(ctx, "python-service"), target)
            manifest = json.loads((target / PROFILE_MANIFEST_REL).read_text(encoding="utf-8"))

            self.assertEqual(manifest["variables"][0]["name"], "python_bin")
            self.assertEqual(manifest["detectors"][0]["id"], "python_project")
            self.assertEqual(manifest["overlays"][0]["managed_by"], "profile-render")

    def test_apply_profile_dry_run_does_not_write_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            ctx = self._build_context(root)
            _write_text(
                root / "profiles" / "python-service.yaml",
                '{"id":"python-service","display_name":"Python Service","applies_to":["backend"],"standards":["standards/python/base.instructions.md"],"templates":["templates/profile/python-service/AGENTS.example.md"],"commands":{},"bootstrap":{"create":["docs/"]}}\n',
            )
            _write_text(root / "standards" / "python" / "base.instructions.md", "# Python Base\n")
            _write_text(root / "templates" / "profile" / "python-service" / "AGENTS.example.md", "# Target AGENTS\n")

            result = apply_profile(ctx, load_profile(ctx, "python-service"), target, dry_run=True)

            self.assertEqual(result.created_dirs, ["docs"])
            self.assertFalse((target / "docs").exists())
            self.assertFalse((target / "AGENTS.md").exists())

    def test_apply_profile_generates_agents_router_without_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            ctx = self._build_context(root)
            _write_text(
                root / "profiles" / "frontend-app.yaml",
                '{"id":"frontend-app","display_name":"Frontend App","applies_to":["frontend"],"standards":["standards/docs/docs-sync.instructions.md"],"templates":[],"commands":{},"bootstrap":{"create":["docs/"]}}\n',
            )
            _write_text(root / "standards" / "docs" / "docs-sync.instructions.md", "# Docs Sync\n")

            result = apply_profile(ctx, load_profile(ctx, "frontend-app"), target)

            agents_text = (target / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("agents-memory-bridge.instructions.md", agents_text)
            self.assertIn(".github/instructions/agents-memory/standards/docs/docs-sync.instructions.md", agents_text)
            self.assertEqual(result.managed_files, ["AGENTS.md"])

    def test_apply_profile_writes_project_facts_from_detectors(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            ctx = self._build_context(root)
            _write_text(target / "pyproject.toml", "[project]\nname='demo'\n")
            _write_text(
                root / "profiles" / "python-service.yaml",
                '{"id":"python-service","display_name":"Python Service","applies_to":["backend"],"standards":[],"templates":[],"variables":[{"name":"python_bin","description":"Python executable","default":"python3","required":false}],"detectors":[{"id":"python_project","kind":"path_exists","output":"language.python","config":{"any_of":["pyproject.toml"]}}],"overlays":[],"commands":{},"bootstrap":{"create":[]}}\n',
            )

            apply_profile(ctx, load_profile(ctx, "python-service"), target)
            facts = json.loads((target / PROJECT_FACTS_REL).read_text(encoding="utf-8"))

            self.assertEqual(facts["profile_id"], "python-service")
            self.assertEqual(facts["variables"]["python_bin"], "python3")
            self.assertTrue(facts["facts"]["language.python"])

    def test_apply_profile_writes_project_facts_for_extended_detector_kinds(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            ctx = self._build_context(root)
            _write_text(target / "pyproject.toml", "[tool.pytest.ini_options]\naddopts='-q'\n")
            _write_text(target / "package.json", '{"packageManager":"pnpm@10","scripts":{"test":"vitest"}}\n')
            _write_text(
                root / "profiles" / "python-service.yaml",
                '{"id":"python-service","display_name":"Python Service","applies_to":["backend"],"standards":[],"templates":[],"detectors":[{"id":"python_project","kind":"path_exists","output":"language.python","config":{"any_of":["pyproject.toml"]}},{"id":"pytest_configured","kind":"file_contains","output":"testing.pytest","config":{"path":"pyproject.toml","any_of":["pytest"]}},{"id":"package_manager_declared","kind":"json_key_exists","output":"node.package_manager","config":{"path":"package.json","all_of":["packageManager","scripts.test"]}},{"id":"python_runtime","kind":"command_available","output":"runtime.python","config":{"any_of":["python3"]}},{"id":"missing_command","kind":"command_available","output":"runtime.fake","config":{"any_of":["definitely-not-a-real-command-amem"]}}],"overlays":[],"commands":{},"bootstrap":{"create":[]}}\n',
            )

            apply_profile(ctx, load_profile(ctx, "python-service"), target)
            facts = json.loads((target / PROJECT_FACTS_REL).read_text(encoding="utf-8"))

            self.assertTrue(facts["facts"]["language.python"])
            self.assertTrue(facts["facts"]["testing.pytest"])
            self.assertTrue(facts["facts"]["node.package_manager"])
            self.assertTrue(facts["facts"]["runtime.python"])
            self.assertFalse(facts["facts"]["runtime.fake"])
            self.assertIn("pyproject.toml:pytest", facts["detectors"][1]["matched_paths"])
            self.assertIn("package.json:packageManager", facts["detectors"][2]["matched_paths"])
            self.assertIn("python3", facts["detectors"][3]["matched_paths"])

    def test_profile_check_reports_ok_for_applied_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            ctx = self._build_context(root)
            _write_text(
                root / "profiles" / "python-service.yaml",
                '{"id":"python-service","display_name":"Python Service","applies_to":["backend"],"standards":["standards/python/base.instructions.md"],"templates":["templates/profile/python-service/AGENTS.example.md"],"variables":[{"name":"python_bin","description":"Python executable","default":"python3","required":false}],"detectors":[{"id":"python_project","kind":"path_exists","output":"language.python","config":{"any_of":["pyproject.toml"]}}],"overlays":[{"target":".github/instructions/agents-memory/project-local.instructions.md","template":"templates/profile/python-service/project-local.instructions.example.md","variables":["python_bin"],"detectors":["python_project"],"managed_by":"profile-render"}],"commands":{"docs_check":"amem docs-check ."},"bootstrap":{"create":["docs/","tests/"]}}\n',
            )
            _write_text(root / "standards" / "python" / "base.instructions.md", "# Python Base\n")
            _write_text(root / "templates" / "profile" / "python-service" / "AGENTS.example.md", "# Target AGENTS\n")
            _write_text(root / "templates" / "profile" / "python-service" / "project-local.instructions.example.md", "python={{variable.python_bin}}\nactive={{fact.language.python}}\n")
            _write_text(target / "pyproject.toml", "[project]\nname='demo'\n")

            apply_profile(ctx, load_profile(ctx, "python-service"), target)
            findings = collect_profile_check_findings(ctx, target)

            self.assertFalse(any(f.status == "FAIL" for f in findings))

    def test_profile_check_flags_missing_installed_standard(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            ctx = self._build_context(root)
            _write_text(
                root / "profiles" / "python-service.yaml",
                '{"id":"python-service","display_name":"Python Service","applies_to":["backend"],"standards":["standards/python/base.instructions.md"],"templates":["templates/profile/python-service/AGENTS.example.md"],"commands":{"docs_check":"amem docs-check ."},"bootstrap":{"create":["docs/"]}}\n',
            )
            _write_text(root / "standards" / "python" / "base.instructions.md", "# Python Base\n")
            _write_text(root / "templates" / "profile" / "python-service" / "AGENTS.example.md", "# Target AGENTS\n")

            apply_profile(ctx, load_profile(ctx, "python-service"), target)
            (target / ".github" / "instructions" / "agents-memory" / "standards" / "python" / "base.instructions.md").unlink()

            findings = collect_profile_check_findings(ctx, target)

            self.assertTrue(any(f.status == "FAIL" and f.key == "profile_standard_files" for f in findings))

    def test_profile_check_flags_missing_project_facts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            ctx = self._build_context(root)
            _write_text(
                root / "profiles" / "python-service.yaml",
                '{"id":"python-service","display_name":"Python Service","applies_to":["backend"],"standards":[],"templates":[],"detectors":[],"overlays":[],"commands":{},"bootstrap":{"create":[]}}\n',
            )

            apply_profile(ctx, load_profile(ctx, "python-service"), target)
            (target / PROJECT_FACTS_REL).unlink()

            findings = collect_profile_check_findings(ctx, target)

            self.assertTrue(any(f.status == "FAIL" and f.key == "profile_project_facts" for f in findings))

    def test_apply_profile_renders_active_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            ctx = self._build_context(root)
            _write_text(target / "pyproject.toml", "[project]\nname='demo'\n")
            _write_text(
                root / "profiles" / "python-service.yaml",
                '{"id":"python-service","display_name":"Python Service","applies_to":["backend"],"standards":[],"templates":[],"variables":[{"name":"python_bin","description":"Python executable","default":"python3","required":false}],"detectors":[{"id":"python_project","kind":"path_exists","output":"language.python","config":{"any_of":["pyproject.toml"]}}],"overlays":[{"target":".github/instructions/agents-memory/project-local.instructions.md","template":"templates/profile/python-service/project-local.instructions.example.md","variables":["python_bin"],"detectors":["python_project"],"managed_by":"profile-render"}],"commands":{},"bootstrap":{"create":[]}}\n',
            )
            _write_text(root / "templates" / "profile" / "python-service" / "project-local.instructions.example.md", "python={{variable.python_bin}}\nactive={{fact.language.python}}\n")

            result = apply_profile(ctx, load_profile(ctx, "python-service"), target)

            overlay_path = target / ".github" / "instructions" / "agents-memory" / "project-local.instructions.md"
            self.assertIn(".github/instructions/agents-memory/project-local.instructions.md", result.rendered_overlays)
            self.assertEqual(overlay_path.read_text(encoding="utf-8"), "python=python3\nactive=true\n")

    def test_profile_render_removes_inactive_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            ctx = self._build_context(root)
            _write_text(
                root / "profiles" / "python-service.yaml",
                '{"id":"python-service","display_name":"Python Service","applies_to":["backend"],"standards":[],"templates":[],"variables":[{"name":"python_bin","description":"Python executable","default":"python3","required":false}],"detectors":[{"id":"python_project","kind":"path_exists","output":"language.python","config":{"any_of":["pyproject.toml"]}}],"overlays":[{"target":".github/instructions/agents-memory/project-local.instructions.md","template":"templates/profile/python-service/project-local.instructions.example.md","variables":["python_bin"],"detectors":["python_project"],"managed_by":"profile-render"}],"commands":{},"bootstrap":{"create":[]}}\n',
            )
            _write_text(root / "templates" / "profile" / "python-service" / "project-local.instructions.example.md", "python={{variable.python_bin}}\n")
            overlay_path = target / ".github" / "instructions" / "agents-memory" / "project-local.instructions.md"
            _write_text(overlay_path, "stale\n")

            result = render_profile_overlays(ctx, load_profile(ctx, "python-service"), target)

            self.assertIn(".github/instructions/agents-memory/project-local.instructions.md", result.removed_overlays)
            self.assertFalse(overlay_path.exists())

    def test_profile_check_flags_stale_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            ctx = self._build_context(root)
            _write_text(target / "pyproject.toml", "[project]\nname='demo'\n")
            _write_text(
                root / "profiles" / "python-service.yaml",
                '{"id":"python-service","display_name":"Python Service","applies_to":["backend"],"standards":[],"templates":[],"variables":[{"name":"python_bin","description":"Python executable","default":"python3","required":false}],"detectors":[{"id":"python_project","kind":"path_exists","output":"language.python","config":{"any_of":["pyproject.toml"]}}],"overlays":[{"target":".github/instructions/agents-memory/project-local.instructions.md","template":"templates/profile/python-service/project-local.instructions.example.md","variables":["python_bin"],"detectors":["python_project"],"managed_by":"profile-render"}],"commands":{},"bootstrap":{"create":[]}}\n',
            )
            _write_text(root / "templates" / "profile" / "python-service" / "project-local.instructions.example.md", "python={{variable.python_bin}}\nactive={{fact.language.python}}\n")

            apply_profile(ctx, load_profile(ctx, "python-service"), target)
            (target / ".github" / "instructions" / "agents-memory" / "project-local.instructions.md").write_text("stale\n", encoding="utf-8")

            findings = collect_profile_check_findings(ctx, target)

            self.assertTrue(any(f.status == "FAIL" and f.key == "profile_overlay_files" for f in findings))

    def test_sync_profile_standards_updates_managed_standard_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            ctx = self._build_context(root)
            _write_text(
                root / "profiles" / "python-service.yaml",
                '{"id":"python-service","display_name":"Python Service","applies_to":["backend"],"standards":["standards/python/base.instructions.md"],"templates":[],"commands":{"docs_check":"amem docs-check ."},"bootstrap":{"create":[]}}\n',
            )
            _write_text(root / "standards" / "python" / "base.instructions.md", "# Python Base v2\n")

            profile = load_profile(ctx, "python-service")
            apply_profile(ctx, profile, target)
            installed_standard = target / ".github" / "instructions" / "agents-memory" / "standards" / "python" / "base.instructions.md"
            installed_standard.write_text("# old\n", encoding="utf-8")

            result = sync_profile_standards(ctx, profile, target)

            self.assertEqual(installed_standard.read_text(encoding="utf-8"), "# Python Base v2\n")
            self.assertIn(".github/instructions/agents-memory/standards/python/base.instructions.md", result.synced_standards)
            self.assertFalse(result.missing_sources)

    def test_sync_profile_standards_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            ctx = self._build_context(root)
            _write_text(
                root / "profiles" / "python-service.yaml",
                '{"id":"python-service","display_name":"Python Service","applies_to":["backend"],"standards":["standards/python/base.instructions.md"],"templates":[],"commands":{"docs_check":"amem docs-check ."},"bootstrap":{"create":[]}}\n',
            )
            _write_text(root / "standards" / "python" / "base.instructions.md", "# Python Base v2\n")

            profile = load_profile(ctx, "python-service")
            apply_profile(ctx, profile, target)
            installed_standard = target / ".github" / "instructions" / "agents-memory" / "standards" / "python" / "base.instructions.md"
            installed_standard.write_text("# old\n", encoding="utf-8")

            result = sync_profile_standards(ctx, profile, target, dry_run=True)

            self.assertEqual(installed_standard.read_text(encoding="utf-8"), "# old\n")
            self.assertIn(".github/instructions/agents-memory/standards/python/base.instructions.md", result.synced_standards)
            self.assertTrue(result.dry_run)

    def test_sync_profile_standards_refreshes_stale_agents_router(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            ctx = self._build_context(root)
            _write_text(
                root / "profiles" / "python-service.yaml",
                '{"id":"python-service","display_name":"Python Service","applies_to":["backend"],"standards":["standards/python/base.instructions.md","standards/docs/docs-sync.instructions.md"],"templates":[],"commands":{},"bootstrap":{"create":[]}}\n',
            )
            _write_text(root / "standards" / "python" / "base.instructions.md", "# Python Base\n")
            _write_text(root / "standards" / "docs" / "docs-sync.instructions.md", "# Docs Sync\n")

            profile = load_profile(ctx, "python-service")
            apply_profile(ctx, profile, target)
            (target / "AGENTS.md").write_text("# AGENTS\n\nLegacy notes only\n", encoding="utf-8")

            result = sync_profile_standards(ctx, profile, target)

            content = (target / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("agents-memory-bridge.instructions.md", content)
            self.assertIn("standards/python/base.instructions.md", content)
            self.assertIn("AGENTS.md", result.synced_managed_files)

    def test_sync_profile_standards_refreshes_stale_project_facts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            ctx = self._build_context(root)
            _write_text(target / "pyproject.toml", "[project]\nname='demo'\n")
            _write_text(
                root / "profiles" / "python-service.yaml",
                '{"id":"python-service","display_name":"Python Service","applies_to":["backend"],"standards":[],"templates":[],"detectors":[{"id":"python_project","kind":"path_exists","output":"language.python","config":{"any_of":["pyproject.toml"]}}],"overlays":[],"commands":{},"bootstrap":{"create":[]}}\n',
            )

            profile = load_profile(ctx, "python-service")
            apply_profile(ctx, profile, target)
            (target / PROJECT_FACTS_REL).write_text('{"profile_id":"python-service","facts":{"language.python":false}}\n', encoding="utf-8")

            sync_profile_standards(ctx, profile, target)
            facts = json.loads((target / PROJECT_FACTS_REL).read_text(encoding="utf-8"))

            self.assertTrue(facts["facts"]["language.python"])

    def test_sync_profile_standards_refreshes_stale_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            ctx = self._build_context(root)
            _write_text(target / "pyproject.toml", "[project]\nname='demo'\n")
            _write_text(
                root / "profiles" / "python-service.yaml",
                '{"id":"python-service","display_name":"Python Service","applies_to":["backend"],"standards":[],"templates":[],"variables":[{"name":"python_bin","description":"Python executable","default":"python3","required":false}],"detectors":[{"id":"python_project","kind":"path_exists","output":"language.python","config":{"any_of":["pyproject.toml"]}}],"overlays":[{"target":".github/instructions/agents-memory/project-local.instructions.md","template":"templates/profile/python-service/project-local.instructions.example.md","variables":["python_bin"],"detectors":["python_project"],"managed_by":"profile-render"}],"commands":{},"bootstrap":{"create":[]}}\n',
            )
            _write_text(root / "templates" / "profile" / "python-service" / "project-local.instructions.example.md", "python={{variable.python_bin}}\nactive={{fact.language.python}}\n")

            profile = load_profile(ctx, "python-service")
            apply_profile(ctx, profile, target)
            (target / ".github" / "instructions" / "agents-memory" / "project-local.instructions.md").write_text("stale\n", encoding="utf-8")

            result = sync_profile_standards(ctx, profile, target)
            overlay_text = (target / ".github" / "instructions" / "agents-memory" / "project-local.instructions.md").read_text(encoding="utf-8")

            self.assertIn(".github/instructions/agents-memory/project-local.instructions.md", result.synced_overlays)
            self.assertEqual(overlay_text, "python=python3\nactive=true\n")
