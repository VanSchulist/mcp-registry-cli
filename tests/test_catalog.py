"""Unit tests for catalog data integrity and configuration conversion."""

import unittest
from mcp_registry.catalog import CATALOG, MCPServerEntry


class TestCatalog(unittest.TestCase):
    def test_catalog_entries_count(self):
        """Ensures catalog contains a healthy set of verified servers."""
        self.assertGreaterEqual(len(CATALOG), 20)

    def test_catalog_entry_integrity(self):
        """Validates that each catalog entry has required fields and structure."""
        valid_runtimes = {"node", "python", "docker", "binary"}
        for name, entry in CATALOG.items():
            self.assertEqual(name, entry.name)
            self.assertTrue(entry.display_name, f"Empty display_name for {name}")
            self.assertTrue(entry.description, f"Empty description for {name}")
            self.assertTrue(entry.category, f"Empty category for {name}")
            self.assertIn(entry.runtime, valid_runtimes, f"Invalid runtime for {name}: {entry.runtime}")
            self.assertTrue(entry.command, f"Empty command for {name}")
            self.assertIsInstance(entry.args, list)
            self.assertIsInstance(entry.env, dict)
            self.assertIsInstance(entry.tools, list)

    def test_to_mcp_config_basic(self):
        """Tests standard conversion to MCP client config dictionary."""
        entry = CATALOG.get("git")
        self.assertIsNotNone(entry)
        cfg = entry.to_mcp_config()
        self.assertEqual(cfg["command"], "python")
        self.assertEqual(cfg["args"], ["-m", "mcp_server_git"])

    def test_to_mcp_config_with_env(self):
        """Tests env overrides applied during MCP config conversion."""
        entry = CATALOG.get("github")
        self.assertIsNotNone(entry)
        cfg = entry.to_mcp_config(env_overrides={"GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_mocktoken123"})
        self.assertIn("env", cfg)
        self.assertEqual(cfg["env"]["GITHUB_PERSONAL_ACCESS_TOKEN"], "ghp_mocktoken123")


if __name__ == "__main__":
    unittest.main()
