from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from agents_memory.runtime import build_context
from agents_memory.services.profiles import apply_profile, list_profiles, load_profile


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
                '{"id":"python-service","display_name":"Python Service","applies_to":["backend","fastapi"],"standards":["standards/python/base.instructions.md"],"templates":["templates/profile/python-service/AGENTS.example.md"],"commands":{"docs_check":"amem docs-check"},"bootstrap":{"create":["docs/"]}}\n',
            )

            profile = load_profile(ctx, "python-service")

            self.assertEqual(profile.display_name, "Python Service")
            self.assertEqual(profile.applies_to, ["backend", "fastapi"])
            self.assertEqual(profile.bootstrap_create, ["docs/"])

    def test_apply_profile_creates_dirs_and_installs_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "target"
            target.mkdir()
            ctx = self._build_context(root)
            _write_text(
                root / "profiles" / "python-service.yaml",
                '{"id":"python-service","display_name":"Python Service","applies_to":["backend"],"standards":["standards/python/base.instructions.md"],"templates":["templates/profile/python-service/AGENTS.example.md"],"commands":{"docs_check":"amem docs-check","doctor":"amem doctor"},"bootstrap":{"create":["docs/","tests/"]}}\n',
            )
            _write_text(root / "standards" / "python" / "base.instructions.md", "# Python Base\n")
            _write_text(root / "templates" / "profile" / "python-service" / "AGENTS.example.md", "# Target AGENTS\n")

            result = apply_profile(ctx, load_profile(ctx, "python-service"), target)

            self.assertTrue((target / "docs").exists())
            self.assertTrue((target / "tests").exists())
            self.assertTrue((target / ".github" / "instructions" / "agents-memory" / "standards" / "python" / "base.instructions.md").exists())
            self.assertTrue((target / "AGENTS.md").exists())
            self.assertEqual(len(result.installed_standards), 1)
            self.assertEqual(len(result.wrote_templates), 1)

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