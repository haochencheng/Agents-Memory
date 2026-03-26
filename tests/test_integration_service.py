from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from agents_memory.runtime import build_context
from agents_memory.services.integration import cmd_bridge_install, write_vscode_mcp_json


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
