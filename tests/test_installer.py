"""Unit tests for MCPInstaller configuration management."""

import json
import tempfile
import unittest
from pathlib import Path
from mcp_registry.catalog import MCPServerEntry
from mcp_registry.installer import MCPInstaller, TargetClient


class TestMCPInstaller(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)
        self.mock_entry = MCPServerEntry(
            name="test-server",
            display_name="Test Server",
            description="Testing installer",
            category="testing",
            runtime="node",
            command="npx",
            args=["-y", "@test/server"],
            env={"API_KEY": {"description": "Test Key", "required": "true"}},
            stars=10,
        )

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_install_mcp_mesh_target(self):
        config_file = self.tmp_path / "mcp_mesh.json"
        installer = MCPInstaller(target_type=TargetClient.MCP_MESH, custom_path=config_file)

        # Dry run does not write
        ok, msg = installer.install(self.mock_entry, dry_run=True)
        self.assertTrue(ok)
        self.assertFalse(config_file.exists())

        # Real install writes to "servers" dict
        ok, msg = installer.install(self.mock_entry, env_overrides={"API_KEY": "secret_123"}, dry_run=False)
        self.assertTrue(ok)
        self.assertTrue(config_file.exists())

        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("servers", data)
        self.assertIn("test-server", data["servers"])
        self.assertEqual(data["servers"]["test-server"]["command"], "npx")
        self.assertEqual(data["servers"]["test-server"]["env"]["API_KEY"], "secret_123")

        # Check is_installed
        self.assertTrue(installer.is_installed("test-server"))
        self.assertFalse(installer.is_installed("other-server"))

    def test_install_claude_target(self):
        config_file = self.tmp_path / "claude_desktop_config.json"
        installer = MCPInstaller(target_type=TargetClient.CLAUDE, custom_path=config_file)

        ok, msg = installer.install(self.mock_entry, dry_run=False)
        self.assertTrue(ok)

        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Claude uses "mcpServers"
        self.assertIn("mcpServers", data)
        self.assertIn("test-server", data["mcpServers"])

    def test_install_antigravity_target(self):
        config_file = self.tmp_path / "mcp_config.json"
        installer = MCPInstaller(target_type=TargetClient.ANTIGRAVITY, custom_path=config_file)

        ok, msg = installer.install(self.mock_entry, dry_run=False)
        self.assertTrue(ok)

        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Antigravity uses "mcpServers"
        self.assertIn("mcpServers", data)
        self.assertIn("test-server", data["mcpServers"])
        self.assertEqual(data["mcpServers"]["test-server"]["command"], "npx")

    def test_uninstall(self):
        config_file = self.tmp_path / "mcp_mesh.json"
        installer = MCPInstaller(target_type=TargetClient.MCP_MESH, custom_path=config_file)

        installer.install(self.mock_entry)
        self.assertTrue(installer.is_installed("test-server"))

        ok, msg = installer.uninstall("test-server")
        self.assertTrue(ok)
        self.assertFalse(installer.is_installed("test-server"))

        # Verify backup was created
        bak_file = config_file.with_suffix(".json.bak")
        self.assertTrue(bak_file.exists())


if __name__ == "__main__":
    unittest.main()
