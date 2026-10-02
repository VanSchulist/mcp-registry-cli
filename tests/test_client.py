"""Unit tests for RegistryClient searching and querying."""

import json
import tempfile
import unittest
from pathlib import Path
from mcp_registry.client import RegistryClient


class TestRegistryClient(unittest.TestCase):
    def setUp(self):
        self.client = RegistryClient()

    def test_get_existing_server(self):
        entry = self.client.get("github")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.name, "github")

    def test_get_case_insensitive(self):
        entry = self.client.get("GitHuB")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.name, "github")

    def test_get_nonexistent_server(self):
        entry = self.client.get("nonexistent_unknown_server_xyz")
        self.assertIsNone(entry)

    def test_search_by_query(self):
        results = self.client.search("postgres")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].name, "postgres")

    def test_search_by_category(self):
        dev_tools = self.client.search(category="developer-tools")
        self.assertGreaterEqual(len(dev_tools), 3)
        for entry in dev_tools:
            self.assertEqual(entry.category, "developer-tools")

    def test_search_by_runtime(self):
        python_tools = self.client.search(runtime="python")
        self.assertGreaterEqual(len(python_tools), 1)
        for entry in python_tools:
            self.assertEqual(entry.runtime, "python")

    def test_list_all_sorted_by_stars(self):
        all_entries = self.client.list_all(sort_by_stars=True)
        self.assertGreater(len(all_entries), 10)
        # Verify descending order of stars
        for i in range(len(all_entries) - 1):
            self.assertGreaterEqual(all_entries[i].stars, all_entries[i + 1].stars)

    def test_list_categories(self):
        cats = self.client.list_categories()
        self.assertIn("developer-tools", cats)
        self.assertIn("database", cats)

    def test_custom_catalog_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({
                "custom-server": {
                    "display_name": "Custom Server",
                    "description": "My private tool",
                    "category": "internal",
                    "runtime": "python",
                    "command": "python",
                    "args": ["-m", "custom"],
                    "stars": 999
                }
            }, f)
            custom_path = f.name

        try:
            custom_client = RegistryClient(custom_catalog_path=custom_path)
            res = custom_client.get("custom-server")
            self.assertIsNotNone(res)
            self.assertEqual(res.display_name, "Custom Server")
        finally:
            Path(custom_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
