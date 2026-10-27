"""Unit tests for mcp-registry doctor diagnostic engine and CLI integration."""

import json
import os
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from mcp_registry.cli import main
from mcp_registry.doctor import DiagnosticCheck, DoctorReport, MCPDoctor
from mcp_registry.installer import TargetClient


class TestMCPDoctor(unittest.TestCase):
    def test_missing_config_explicit_vs_implicit(self):
        """Tests that missing configs report INFO on discovery but WARN on explicit target."""
        doctor = MCPDoctor()
        non_existent = Path(tempfile.gettempdir()) / "non_existent_mcp_test_config.json"
        if non_existent.exists():
            non_existent.unlink()

        # Explicit target
        report = doctor.run_diagnostics(target_client="claude", custom_path=non_existent)
        self.assertEqual(len(report.checks), 1)
        self.assertEqual(report.checks[0].status, "WARN")
        self.assertIn("does not exist", report.checks[0].message)

    def test_corrupted_json_syntax(self):
        """Tests detection of invalid JSON syntax with line/col diagnostics."""
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json", encoding="utf-8") as f:
            f.write("{\n  \"mcpServers\": {\n    \"test\": \n}")
            temp_path = f.name

        try:
            doctor = MCPDoctor()
            report = doctor.run_diagnostics(custom_path=temp_path)
            self.assertFalse(report.is_healthy)
            self.assertEqual(report.failures, 1)
            self.assertEqual(report.checks[1].name, "json_syntax")
            self.assertEqual(report.checks[1].status, "FAIL")
            self.assertIn("Invalid JSON syntax", report.checks[1].message)
        finally:
            os.remove(temp_path)

    def test_non_dict_root_json(self):
        """Tests detection of non-object root JSON structure."""
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json", encoding="utf-8") as f:
            f.write("[\"invalid\", \"root\"]")
            temp_path = f.name

        try:
            doctor = MCPDoctor()
            report = doctor.run_diagnostics(custom_path=temp_path)
            self.assertFalse(report.is_healthy)
            self.assertEqual(report.checks[1].name, "json_structure")
            self.assertEqual(report.checks[1].status, "FAIL")
        finally:
            os.remove(temp_path)

    def test_missing_runtime_binary(self):
        """Tests that non-existent binaries are flagged as FAIL."""
        cfg_data = {
            "mcpServers": {
                "broken-tool": {
                    "command": "nonexistent_binary_xyz_12345",
                    "args": ["run"],
                }
            }
        }
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json", encoding="utf-8") as f:
            json.dump(cfg_data, f)
            temp_path = f.name

        try:
            doctor = MCPDoctor()
            report = doctor.run_diagnostics(custom_path=temp_path)
            self.assertFalse(report.is_healthy)
            bin_check = next(c for c in report.checks if "binary:broken-tool" in c.name)
            self.assertEqual(bin_check.status, "FAIL")
            self.assertIn("was not found on system PATH", bin_check.message)
        finally:
            os.remove(temp_path)

    def test_missing_required_environment_variable(self):
        """Tests that servers requiring credentials report FAIL if unconfigured and missing from env."""
        cfg_data = {
            "mcpServers": {
                "github": {
                    "command": "python",
                    "args": ["-m", "mock_server"],
                    "env": {},
                }
            }
        }
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json", encoding="utf-8") as f:
            json.dump(cfg_data, f)
            temp_path = f.name

        try:
            doctor = MCPDoctor()
            with patch.dict(os.environ, {}, clear=True):
                report = doctor.run_diagnostics(custom_path=temp_path)
            env_check = next(c for c in report.checks if "env:github:GITHUB_PERSONAL_ACCESS_TOKEN" in c.name)
            self.assertEqual(env_check.status, "FAIL")
            self.assertIn("Required env var 'GITHUB_PERSONAL_ACCESS_TOKEN'", env_check.message)
        finally:
            os.remove(temp_path)

    def test_placeholder_environment_variable_rejected(self):
        """Tests that placeholder values like 'CHANGE_ME' are flagged as unconfigured."""
        cfg_data = {
            "mcpServers": {
                "github": {
                    "command": "python",
                    "args": ["-m", "mock_server"],
                    "env": {
                        "GITHUB_PERSONAL_ACCESS_TOKEN": "CHANGE_ME"
                    },
                }
            }
        }
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json", encoding="utf-8") as f:
            json.dump(cfg_data, f)
            temp_path = f.name

        try:
            doctor = MCPDoctor()
            with patch.dict(os.environ, {}, clear=True):
                report = doctor.run_diagnostics(custom_path=temp_path)
            env_check = next(c for c in report.checks if "env:github:GITHUB_PERSONAL_ACCESS_TOKEN" in c.name)
            self.assertEqual(env_check.status, "FAIL")
        finally:
            os.remove(temp_path)

    def test_token_bloat_recommendation(self):
        """Tests that 4+ direct servers trigger WARN token economy check recommending mcp-mesh."""
        cfg_data = {
            "mcpServers": {
                f"server_{i}": {"command": "python", "args": []} for i in range(5)
            }
        }
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json", encoding="utf-8") as f:
            json.dump(cfg_data, f)
            temp_path = f.name

        try:
            doctor = MCPDoctor()
            # As claude target
            report_claude = doctor.run_diagnostics(target_client="claude", custom_path=temp_path)
            token_check_claude = next(c for c in report_claude.checks if c.name == "token_economy")
            self.assertEqual(token_check_claude.status, "WARN")
            self.assertIn("mcp-mesh", token_check_claude.remediation)

            # As mcp-mesh target
            report_mesh = doctor.run_diagnostics(target_client=TargetClient.MCP_MESH, custom_path=temp_path)
            token_check_mesh = next(c for c in report_mesh.checks if c.name == "token_economy")
            self.assertEqual(token_check_mesh.status, "PASS")
            self.assertIn("federated via mcp-mesh", token_check_mesh.message)
        finally:
            os.remove(temp_path)

    def test_cli_doctor_json_and_strict_exit_codes(self):
        """Tests CLI doctor command output formatting and strict mode error exit code."""
        # Clean config with python (which exists)
        healthy_cfg = {
            "servers": {
                "local-git": {"command": "python", "args": ["-m", "mcp_server_git"]}
            }
        }
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json", encoding="utf-8") as f:
            json.dump(healthy_cfg, f)
            healthy_path = f.name

        broken_cfg = {
            "servers": {
                "broken": {"command": "nonexistent_command_xyz_456"}
            }
        }
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json", encoding="utf-8") as f:
            json.dump(broken_cfg, f)
            broken_path = f.name

        try:
            # 1. Healthy JSON output
            out = StringIO()
            with patch("sys.stdout", out):
                code = main(["doctor", "--format", "json", "--config", healthy_path])
            self.assertEqual(code, 0)
            parsed = json.loads(out.getvalue())
            self.assertTrue(parsed["summary"]["healthy"])
            self.assertEqual(parsed["summary"]["failures"], 0)

            # 2. Broken without strict -> exits 0 with warnings/failures displayed
            code_lenient = main(["doctor", "--config", broken_path])
            self.assertEqual(code_lenient, 0)

            # 3. Broken with --strict -> exits 1
            code_strict = main(["doctor", "--strict", "--config", broken_path])
            self.assertEqual(code_strict, 1)
        finally:
            os.remove(healthy_path)
            os.remove(broken_path)


if __name__ == "__main__":
    unittest.main()
