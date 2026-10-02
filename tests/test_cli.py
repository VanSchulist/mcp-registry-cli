"""Unit tests for the mcp-registry CLI commands."""

import unittest
from io import StringIO
from unittest.mock import patch

from mcp_registry.cli import main


class TestCLI(unittest.TestCase):
    def test_cli_banner_help(self):
        with patch("sys.stdout", new=StringIO()) as fake_out:
            code = main([])
            self.assertEqual(code, 0)
            output = fake_out.getvalue()
            self.assertIn("mcp-registry", output)
            self.assertIn("Available subcommands", output)

    def test_cli_search(self):
        with patch("sys.stdout", new=StringIO()) as fake_out:
            code = main(["search", "postgres"])
            self.assertEqual(code, 0)
            output = fake_out.getvalue()
            self.assertIn("postgres", output)
            self.assertIn("database", output)

    def test_cli_search_not_found(self):
        with patch("sys.stdout", new=StringIO()) as fake_out:
            code = main(["search", "nonexistent_query_xyz123"])
            self.assertEqual(code, 0)
            output = fake_out.getvalue()
            self.assertIn("No MCP servers found", output)

    def test_cli_info(self):
        with patch("sys.stdout", new=StringIO()) as fake_out:
            code = main(["info", "github"])
            self.assertEqual(code, 0)
            output = fake_out.getvalue()
            self.assertIn("GitHub Official MCP", output)
            self.assertIn("Exported Tools", output)

    def test_cli_info_not_found(self):
        with patch("sys.stdout", new=StringIO()) as fake_out:
            code = main(["info", "unknown_tool_fake"])
            self.assertEqual(code, 1)
            output = fake_out.getvalue()
            self.assertIn("not found", output)

    def test_cli_list_all(self):
        with patch("sys.stdout", new=StringIO()) as fake_out:
            code = main(["list", "--all"])
            self.assertEqual(code, 0)
            output = fake_out.getvalue()
            self.assertIn("All Available MCP Registry Servers", output)


if __name__ == "__main__":
    unittest.main()
