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
        self.assertTrue((self.repo_root / "scripts" / "local" / "restart.sh").exists())
        self.assertTrue((self.repo_root / "scripts" / "staging" / "restart.sh").exists())
        self.assertTrue((self.repo_root / "scripts" / "prod" / "restart.sh").exists())

    def test_scripts_have_valid_bash_syntax(self) -> None:
        scripts = [
            "scripts/lib/env.sh",
            "scripts/web/manage.sh",
            "scripts/web/restart.sh",
            "scripts/runtime/manage.sh",
            "scripts/runtime/restart.sh",
            "scripts/local/web.sh",
            "scripts/local/runtime.sh",
            "scripts/local/restart.sh",
            "scripts/staging/web.sh",
            "scripts/staging/runtime.sh",
            "scripts/staging/restart.sh",
            "scripts/prod/web.sh",
            "scripts/prod/runtime.sh",
            "scripts/prod/restart.sh",
            "scripts/web-start.sh",
            "scripts/start.sh",
        ]
        for path in scripts:
            with self.subTest(path=path):
                self._run(["bash", "-n", path])

    def test_env_directory_wrappers_dispatch_expected_environment(self) -> None:
        cases = [
            ("scripts/local/web.sh", "local", "10100"),
            ("scripts/staging/web.sh", "staging", "20100"),
            ("scripts/prod/runtime.sh", "prod", "30100"),
        ]
        for script, expected_env, expected_api_port in cases:
            with self.subTest(script=script):
                result = self._run(["sh", script, "config", "--json"])
                payload = json.loads(result.stdout)
                self.assertEqual(payload["environment"], expected_env)
                self.assertEqual(payload["api_port"], expected_api_port)

    def test_sh_can_execute_restart_wrappers_without_unbound_variable(self) -> None:
        scripts = [
            "scripts/runtime/restart.sh",
            "scripts/web/restart.sh",
        ]
        for path in scripts:
            with self.subTest(path=path):
                content = (self.repo_root / path).read_text(encoding="utf-8")
                self.assertNotIn('"${@}"', content)
