from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from agents_memory.runtime import build_context
from agents_memory.services.projects import append_project_entry, parse_projects, resolve_project_target


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class ProjectsServiceTests(unittest.TestCase):
    def _build_context(self, root: Path):
        _write_text(root / "templates" / "index.example.md", "index\n")
        _write_text(root / "templates" / "projects.example.md", "# Project Registry\n\n## 注册新项目\n")
        _write_text(root / "templates" / "rules.example.md", "rules\n")
        previous_root = os.environ.get("AGENTS_MEMORY_ROOT")
        os.environ["AGENTS_MEMORY_ROOT"] = str(root)
        try:
            return build_context(logger_name=f"tests.projects.{root.name}", reference_file=__file__)
        finally:
            if previous_root is None:
                os.environ.pop("AGENTS_MEMORY_ROOT", None)
            else:
                os.environ["AGENTS_MEMORY_ROOT"] = previous_root

    def test_parse_projects_returns_only_active_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = self._build_context(root)
            ctx.projects_file.write_text(
                """# Project Registry

## active-project

- **id**: active-project
- **root**: /tmp/active-project
- **active**: true

## inactive-project

- **id**: inactive-project
- **root**: /tmp/inactive-project
- **active**: false

## 注册新项目
""",
                encoding="utf-8",
            )

            projects = parse_projects(ctx)

            self.assertEqual([project["id"] for project in projects], ["active-project"])

    def test_resolve_project_target_prefers_registered_project_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project_root = root / "registered-project-root"
            project_root.mkdir()
            ctx = self._build_context(root)
            ctx.projects_file.write_text(
                f"""# Project Registry

## spec2flow

- **id**: spec2flow
- **root**: {project_root}
- **active**: true
""",
                encoding="utf-8",
            )

            project_id, resolved_root, project = resolve_project_target(ctx, "spec2flow")

            self.assertEqual(project_id, "spec2flow")
            self.assertEqual(resolved_root, project_root.resolve())
            self.assertIsNotNone(project)

    def test_append_project_entry_inserts_before_registration_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ctx = self._build_context(root)
            ctx.projects_file.write_text("# Project Registry\n\n## 注册新项目\n", encoding="utf-8")

            append_project_entry(
                ctx,
                "## demo\n\n- **id**: demo\n- **root**: /tmp/demo\n- **active**: true\n\n---\n",
            )

            content = ctx.projects_file.read_text(encoding="utf-8")
            self.assertLess(content.index("## demo"), content.index("## 注册新项目"))