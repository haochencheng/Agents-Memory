from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


class ScriptEnvConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]

    def _run(self, cmd: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            cmd,
            cwd=self.repo_root,
            check=True,
            capture_output=True,
            text=True,
        )

    def test_web_start_config_reads_staging_environment(self) -> None:
        result = self._run(["bash", "scripts/web-start.sh", "--env", "staging", "config", "--json"])
        payload = json.loads(result.stdout)
        self.assertEqual(payload["environment"], "staging")
        self.assertEqual(payload["api_port"], "20100")
        self.assertEqual(payload["ui_port"], "20000")
        self.assertEqual(payload["api_proxy_target"], "http://localhost:20100")

    def test_runtime_start_config_reads_prod_environment(self) -> None:
        result = self._run(["bash", "scripts/start.sh", "--env", "prod", "config", "--json"])
        payload = json.loads(result.stdout)
        self.assertEqual(payload["environment"], "prod")
        self.assertEqual(payload["qdrant_port"], "8333")
        self.assertEqual(payload["ollama_port"], "31434")

    def test_grouped_restart_scripts_exist(self) -> None:
        self.assertTrue((self.repo_root / "scripts" / "web" / "restart.sh").exists())
        self.assertTrue((self.repo_root / "scripts" / "runtime" / "restart.sh").exists())

    def test_scripts_have_valid_bash_syntax(self) -> None:
        scripts = [
            "scripts/lib/env.sh",
            "scripts/web/manage.sh",
            "scripts/web/restart.sh",
            "scripts/runtime/manage.sh",
            "scripts/runtime/restart.sh",
            "scripts/web-start.sh",
            "scripts/start.sh",
        ]
        for path in scripts:
            with self.subTest(path=path):
                self._run(["bash", "-n", path])
