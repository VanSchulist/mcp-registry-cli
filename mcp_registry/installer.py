"""Configuration manager and installer for MCP clients (mcp-mesh, Claude Desktop, Cursor)."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .catalog import MCPServerEntry


class TargetClient:
    MCP_MESH = "mcp-mesh"
    CLAUDE = "claude"
    CURSOR = "cursor"
    ANTIGRAVITY = "antigravity"
    CUSTOM = "custom"


class MCPInstaller:
    """Manages injection, update, and removal of MCP server configurations across clients."""

    def __init__(self, target_type: str = TargetClient.MCP_MESH, custom_path: Optional[str | Path] = None) -> None:
        self.target_type = target_type
        self.config_path = Path(custom_path) if custom_path else self._resolve_default_path(target_type)

    @staticmethod
    def _resolve_default_path(target_type: str) -> Path:
        """Resolves the default configuration file path for the specified client."""
        home = Path.home()

        if target_type == TargetClient.MCP_MESH:
            # Check local current directory first, fallback to user global mesh config
            local_mesh = Path("mcp_mesh.json")
            if local_mesh.exists():
                return local_mesh.resolve()
            global_mesh = home / ".mcp-mesh" / "servers.json"
            if global_mesh.exists():
                return global_mesh.resolve()
            return Path("mcp_mesh.json")

        if target_type == TargetClient.ANTIGRAVITY:
            # Google Antigravity global MCP configuration
            return home / ".gemini" / "config" / "mcp_config.json"

        if target_type == TargetClient.CLAUDE:
            if sys.platform == "win32":
                appdata = os.environ.get("APPDATA")
                base = Path(appdata) if appdata else home / "AppData" / "Roaming"
                return base / "Claude" / "claude_desktop_config.json"
            elif sys.platform == "darwin":
                return home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
            else:
                return home / ".config" / "Claude" / "claude_desktop_config.json"

        if target_type == TargetClient.CURSOR:
            local_cursor = Path(".cursor") / "mcp.json"
            if local_cursor.exists() or Path(".cursor").is_dir():
                return local_cursor.resolve()
            local_mcp = Path(".mcp.json")
            if local_mcp.exists():
                return local_mcp.resolve()
            user_cursor = home / ".cursor" / "mcp.json"
            if user_cursor.exists():
                return user_cursor.resolve()
            if sys.platform == "win32":
                appdata = os.environ.get("APPDATA")
                if appdata and (Path(appdata) / "Cursor" / "mcp.json").exists():
                    return (Path(appdata) / "Cursor" / "mcp.json").resolve()
            return Path(".cursor") / "mcp.json"

        return Path("mcp_mesh.json")

    def load_config(self) -> Dict[str, Any]:
        """Loads and parses the target configuration file, returning an empty dict if not found."""
        if not self.config_path.exists():
            return {}
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _get_server_dict(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieves or creates the appropriate server dictionary section."""
        if self.target_type == TargetClient.MCP_MESH:
            if "servers" not in config_data or not isinstance(config_data["servers"], dict):
                config_data["servers"] = {}
            return config_data["servers"]
        else:
            # Claude and Cursor use "mcpServers"
            if "mcpServers" not in config_data or not isinstance(config_data["mcpServers"], dict):
                config_data["mcpServers"] = {}
            return config_data["mcpServers"]

    def is_installed(self, server_name: str) -> bool:
        """Checks if a server is already configured in the target config."""
        config_data = self.load_config()
        servers = self._get_server_dict(config_data)
        return server_name in servers

    def list_installed(self) -> Dict[str, Dict[str, Any]]:
        """Returns all configured servers from the target config."""
        config_data = self.load_config()
        return dict(self._get_server_dict(config_data))

    def install(
        self,
        entry: MCPServerEntry,
        env_overrides: Optional[Dict[str, str]] = None,
        dry_run: bool = False,
        backup: bool = True,
    ) -> Tuple[bool, str]:
        """Installs or updates a server entry in the target configuration file."""
        config_data = self.load_config()
        servers = self._get_server_dict(config_data)

        # Build server definition
        server_def = entry.to_mcp_config(env_overrides=env_overrides)

        # Merge with existing env vars if previously configured
        if entry.name in servers and isinstance(servers[entry.name], dict):
            existing_env = servers[entry.name].get("env", {})
            if isinstance(existing_env, dict):
                merged_env = dict(existing_env)
                if "env" in server_def:
                    merged_env.update(server_def["env"])
                server_def["env"] = merged_env

        servers[entry.name] = server_def

        if dry_run:
            preview_json = json.dumps({entry.name: server_def}, indent=2)
            return True, f"[Dry Run] Successfully prepared configuration for '{entry.name}' (Target: {self.config_path}):\n{preview_json}"

        # Ensure parent directory exists
        if self.config_path.parent and not self.config_path.parent.exists():
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Create backup if file exists
        bak_path: Optional[Path] = None
        if backup and self.config_path.exists():
            bak_path = self.config_path.with_suffix(self.config_path.suffix + ".bak")
            shutil.copy2(self.config_path, bak_path)

        # Write formatted JSON with rollback on failure
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)
            return True, f"Successfully configured '{entry.name}' in {self.config_path}"
        except Exception as e:
            if backup and bak_path and bak_path.exists():
                try:
                    shutil.copy2(bak_path, self.config_path)
                except Exception:
                    pass
            return False, f"Failed to write configuration: {e}"

    def uninstall(self, server_name: str, backup: bool = True) -> Tuple[bool, str]:
        """Removes a server from the target configuration."""
        if not self.config_path.exists():
            return False, f"Configuration file {self.config_path} does not exist."

        config_data = self.load_config()
        servers = self._get_server_dict(config_data)

        if server_name not in servers:
            return False, f"Server '{server_name}' is not installed in {self.config_path}."

        del servers[server_name]

        if backup and self.config_path.exists():
            bak_path = self.config_path.with_suffix(self.config_path.suffix + ".bak")
            shutil.copy2(self.config_path, bak_path)

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)
            return True, f"Successfully removed '{server_name}' from {self.config_path}"
        except Exception as e:
            return False, f"Failed to write updated configuration: {e}"
