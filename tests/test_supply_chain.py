"""Unit tests for supply chain security, version pinning, and installation safety."""

import json
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from mcp_registry.catalog import CATALOG, MCPServerEntry
from mcp_registry.cli import main
from mcp_registry.installer import MCPInstaller, TargetClient


class TestSupplyChainSecurity(unittest.TestCase):
    def test_pinned_versions_on_official_servers(self):
        """Ensures all official node-based servers have pinned versions, not unpinned latest."""
        official_servers = [e for e in CATALOG.values() if e.official]
        self.assertGreater(len(official_servers), 5)
        for entry in official_servers:
            self.assertTrue(entry.version, f"Server '{entry.name}' is missing version pin")
            self.assertTrue(entry.publisher, f"Server '{entry.name}' is missing publisher")
            if entry.runtime == "node" and any("@modelcontextprotocol" in a for a in entry.args):
                # Verify arg has @version
                pkg_arg = [a for a in entry.args if "@modelcontextprotocol" in a][0]
                self.assertIn(f"@{entry.version}", pkg_arg)

    def test_dry_run_detailed_preview(self):
        """Verifies that dry-run returns the target path and formatted JSON preview."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            cfg_path = Path(tmp_dir) / "test_mesh.json"
            installer = MCPInstaller(target_type=TargetClient.MCP_MESH, custom_path=cfg_path)
            entry = CATALOG["github"]
            ok, msg = installer.install(entry, dry_run=True)
            self.assertTrue(ok)
            self.assertIn("[Dry Run]", msg)
            self.assertIn(str(cfg_path), msg)
            self.assertIn("@modelcontextprotocol/server-github@0.6.2", msg)
            # Ensure file was not created
            self.assertFalse(cfg_path.exists())

    def test_backup_and_rollback_on_write_failure(self):
        """Verifies that if writing fails, the original config is preserved."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            cfg_path = Path(tmp_dir) / "test_mesh.json"
            # Pre-populate initial config
            initial_data = {"servers": {"existing": {"command": "echo", "args": ["hi"]}}}
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(initial_data, f)

            installer = MCPInstaller(target_type=TargetClient.MCP_MESH, custom_path=cfg_path)
            entry = CATALOG["sqlite"]

            # Simulate write error
            with patch("json.dump", side_effect=OSError("Disk full simulation")):
                ok, msg = installer.install(entry, backup=True)
                self.assertFalse(ok)
                self.assertIn("Failed to write", msg)

            # File should still be valid initial config
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertIn("existing", data["servers"])
            self.assertNotIn("sqlite", data["servers"])

    def test_cli_install_emits_supply_chain_warning(self):
        """Verifies that installing community servers displays supply chain notice."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            cfg_path = Path(tmp_dir) / "mcp_mesh.json"
            with patch("sys.stdout", new=StringIO()) as fake_out:
                code = main(["add", "docker", "--target", str(cfg_path), "--dry-run"])
                self.assertEqual(code, 0)
                output = fake_out.getvalue()
                self.assertIn("Supply Chain Notice", output)
                self.assertIn("community-contributed", output)


if __name__ == "__main__":
    unittest.main()
