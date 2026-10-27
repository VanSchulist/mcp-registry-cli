"""Diagnostic health check engine for MCP client configurations and runtimes."""

from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .catalog import CATALOG, MCPServerEntry
from .installer import MCPInstaller, TargetClient


@dataclass
class DiagnosticCheck:
    """Represents the outcome of a single diagnostic check."""
    name: str
    target: str
    status: str  # "PASS", "WARN", "FAIL", "INFO"
    message: str
    remediation: str = ""
    server: Optional[str] = None
    config_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "target": self.target,
            "server": self.server,
            "status": self.status,
            "message": self.message,
            "remediation": self.remediation,
            "config_path": self.config_path,
        }


@dataclass
class DoctorReport:
    """Aggregated health report across all diagnostic checks."""
    checks: List[DiagnosticCheck] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for c in self.checks if c.status == "PASS")

    @property
    def warnings(self) -> int:
        return sum(1 for c in self.checks if c.status == "WARN")

    @property
    def failures(self) -> int:
        return sum(1 for c in self.checks if c.status == "FAIL")

    @property
    def infos(self) -> int:
        return sum(1 for c in self.checks if c.status == "INFO")

    @property
    def is_healthy(self) -> bool:
        return self.failures == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": {
                "passed": self.passed,
                "warnings": self.warnings,
                "failures": self.failures,
                "infos": self.infos,
                "healthy": self.is_healthy,
            },
            "checks": [c.to_dict() for c in self.checks],
        }


class MCPDoctor:
    """Audits MCP client configurations, system binaries, environment variables, and token budgets."""

    DEFAULT_CLIENTS = [
        TargetClient.MCP_MESH,
        TargetClient.CLAUDE,
        TargetClient.CURSOR,
        TargetClient.ANTIGRAVITY,
    ]

    PLACEHOLDER_VALUES = {
        "change_me", "changeme", "your_key", "your_token", "your_api_key",
        "replace_me", "todo", "", "none", "null"
    }

    def __init__(self, catalog: Optional[Dict[str, MCPServerEntry]] = None) -> None:
        self.catalog = catalog if catalog is not None else CATALOG

    def run_diagnostics(
        self,
        target_client: str = "all",
        custom_path: Optional[str | Path] = None,
    ) -> DoctorReport:
        """Runs comprehensive diagnostics across specified or all detected client targets."""
        report = DoctorReport()

        if custom_path:
            p = Path(custom_path).resolve()
            client_type = target_client if target_client != "all" else TargetClient.CUSTOM
            checks = self._diagnose_single_target(client_type, p, is_explicit=True)
            report.checks.extend(checks)
            return report

        if target_client != "all":
            installer = MCPInstaller(target_type=target_client)
            checks = self._diagnose_single_target(target_client, installer.config_path, is_explicit=True)
            report.checks.extend(checks)
            return report

        # Diagnose all known clients
        for client in self.DEFAULT_CLIENTS:
            installer = MCPInstaller(target_type=client)
            checks = self._diagnose_single_target(client, installer.config_path, is_explicit=False)
            report.checks.extend(checks)

        return report

    def _diagnose_single_target(
        self,
        target_type: str,
        config_path: Path,
        is_explicit: bool = False,
    ) -> List[DiagnosticCheck]:
        """Audits a single client configuration file and all its declared servers."""
        checks: List[DiagnosticCheck] = []
        path_str = str(config_path)

        # 1. Existence Check
        if not config_path.exists():
            if not is_explicit:
                checks.append(DiagnosticCheck(
                    name="config_existence",
                    target=target_type,
                    status="INFO",
                    message=f"Configuration file not found (client may not be installed).",
                    config_path=path_str,
                ))
                return checks
            else:
                checks.append(DiagnosticCheck(
                    name="config_existence",
                    target=target_type,
                    status="WARN",
                    message=f"Configuration file does not exist at {path_str}.",
                    remediation=f"Initialize by running 'mcp-registry add <server> --client {target_type}'.",
                    config_path=path_str,
                ))
                return checks

        checks.append(DiagnosticCheck(
            name="config_existence",
            target=target_type,
            status="PASS",
            message=f"Configuration file found.",
            config_path=path_str,
        ))

        # 2. Syntax & Parsing Check
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read()
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            checks.append(DiagnosticCheck(
                name="json_syntax",
                target=target_type,
                status="FAIL",
                message=f"Invalid JSON syntax at line {exc.lineno}, column {exc.colno}: {exc.msg}",
                remediation=f"Edit {path_str} to fix JSON formatting or restore from a .bak backup.",
                config_path=path_str,
            ))
            return checks
        except Exception as exc:
            checks.append(DiagnosticCheck(
                name="file_read",
                target=target_type,
                status="FAIL",
                message=f"Failed to read file: {exc}",
                remediation=f"Check file permissions for {path_str}.",
                config_path=path_str,
            ))
            return checks

        if not isinstance(data, dict):
            checks.append(DiagnosticCheck(
                name="json_structure",
                target=target_type,
                status="FAIL",
                message="Root JSON document is not an object/dictionary.",
                remediation=f"Ensure {path_str} has a top-level JSON object.",
                config_path=path_str,
            ))
            return checks

        checks.append(DiagnosticCheck(
            name="json_syntax",
            target=target_type,
            status="PASS",
            message="Valid JSON object structure.",
            config_path=path_str,
        ))

        # 3. Server Registry Section Resolution
        servers_dict: Dict[str, Any] = {}
        if target_type == TargetClient.MCP_MESH:
            if "servers" in data and isinstance(data["servers"], dict):
                servers_dict = data["servers"]
            elif "mcpServers" in data and isinstance(data["mcpServers"], dict):
                servers_dict = data["mcpServers"]
        else:
            if "mcpServers" in data and isinstance(data["mcpServers"], dict):
                servers_dict = data["mcpServers"]
            elif "servers" in data and isinstance(data["servers"], dict):
                servers_dict = data["servers"]

        num_servers = len(servers_dict)
        if num_servers == 0:
            checks.append(DiagnosticCheck(
                name="server_count",
                target=target_type,
                status="INFO",
                message="No MCP servers currently registered in configuration.",
                remediation=f"Use 'mcp-registry add <server> --client {target_type}' to install servers.",
                config_path=path_str,
            ))
            return checks

        # 4. Token Economy Check
        if target_type == TargetClient.MCP_MESH:
            checks.append(DiagnosticCheck(
                name="token_economy",
                target=target_type,
                status="PASS",
                message=f"{num_servers} server(s) federated via mcp-mesh gateway (lazy schema index overhead: ~180 Turn-0 tokens).",
                config_path=path_str,
            ))
        else:
            est_tokens = num_servers * 650
            if num_servers >= 4:
                checks.append(DiagnosticCheck(
                    name="token_economy",
                    target=target_type,
                    status="WARN",
                    message=f"{num_servers} servers eagerly configured (~{est_tokens:,} Turn-0 prompt tokens per turn).",
                    remediation="Run 'mcp-registry sync' to federate all servers via mcp-mesh for 85-95% context reduction.",
                    config_path=path_str,
                ))
            else:
                checks.append(DiagnosticCheck(
                    name="token_economy",
                    target=target_type,
                    status="PASS",
                    message=f"{num_servers} server(s) configured (~{est_tokens:,} Turn-0 tokens). Overhead within manageable limits.",
                    config_path=path_str,
                ))

        # 5. Server-by-Server Audit
        for srv_name, srv_data in servers_dict.items():
            if not isinstance(srv_data, dict):
                checks.append(DiagnosticCheck(
                    name=f"server_structure:{srv_name}",
                    target=target_type,
                    server=srv_name,
                    status="FAIL",
                    message=f"Server definition for '{srv_name}' is not a JSON object.",
                    remediation="Ensure server entry contains 'command' and 'args'.",
                    config_path=path_str,
                ))
                continue

            cmd = srv_data.get("command")
            if not cmd or not isinstance(cmd, str):
                checks.append(DiagnosticCheck(
                    name=f"command_property:{srv_name}",
                    target=target_type,
                    server=srv_name,
                    status="FAIL",
                    message=f"Server '{srv_name}' is missing a valid 'command' string.",
                    remediation="Specify executable command (e.g. 'npx', 'uvx', 'python').",
                    config_path=path_str,
                ))
                continue

            # Command binary existence
            which_path = shutil.which(cmd)
            if not which_path:
                checks.append(DiagnosticCheck(
                    name=f"binary:{srv_name}",
                    target=target_type,
                    server=srv_name,
                    status="FAIL",
                    message=f"Runtime executable '{cmd}' for server '{srv_name}' was not found on system PATH.",
                    remediation=f"Install '{cmd}' and ensure its directory is added to system PATH.",
                    config_path=path_str,
                ))
            else:
                checks.append(DiagnosticCheck(
                    name=f"binary:{srv_name}",
                    target=target_type,
                    server=srv_name,
                    status="PASS",
                    message=f"Executable '{cmd}' located at {which_path}",
                    config_path=path_str,
                ))

            # Args check
            args_val = srv_data.get("args")
            if args_val is not None and not isinstance(args_val, list):
                checks.append(DiagnosticCheck(
                    name=f"args_format:{srv_name}",
                    target=target_type,
                    server=srv_name,
                    status="WARN",
                    message=f"'args' for server '{srv_name}' should be a list of strings.",
                    remediation="Change 'args' to a JSON array of string arguments.",
                    config_path=path_str,
                ))

            # Environment variable validation against catalog
            cat_entry = self._match_catalog_entry(srv_name, srv_data)
            if cat_entry and cat_entry.env:
                srv_env = srv_data.get("env")
                if srv_env is not None and not isinstance(srv_env, dict):
                    checks.append(DiagnosticCheck(
                        name=f"env_format:{srv_name}",
                        target=target_type,
                        server=srv_name,
                        status="WARN",
                        message=f"'env' block for server '{srv_name}' is not a key-value object.",
                        remediation="Ensure 'env' is a dictionary of environment variables.",
                        config_path=path_str,
                    ))
                    srv_env = {}
                elif srv_env is None:
                    srv_env = {}

                for env_var, env_spec in cat_entry.env.items():
                    if env_spec.get("required") == "true":
                        val_in_cfg = srv_env.get(env_var, "")
                        val_in_env = os.environ.get(env_var, "")

                        # Check if configured with real value
                        is_cfg_valid = bool(val_in_cfg and str(val_in_cfg).strip().lower() not in self.PLACEHOLDER_VALUES)
                        is_env_valid = bool(val_in_env and str(val_in_env).strip().lower() not in self.PLACEHOLDER_VALUES)

                        if not is_cfg_valid and not is_env_valid:
                            desc = env_spec.get("description", "Required credential")
                            checks.append(DiagnosticCheck(
                                name=f"env:{srv_name}:{env_var}",
                                target=target_type,
                                server=srv_name,
                                status="FAIL",
                                message=f"Required env var '{env_var}' ({desc}) is not set in config or shell.",
                                remediation=f"Configure '{env_var}' in server 'env' block or run 'export {env_var}=...'.",
                                config_path=path_str,
                            ))
                        else:
                            source = "config" if is_cfg_valid else "environment"
                            checks.append(DiagnosticCheck(
                                name=f"env:{srv_name}:{env_var}",
                                target=target_type,
                                server=srv_name,
                                status="PASS",
                                message=f"Required env var '{env_var}' is configured (via {source}).",
                                config_path=path_str,
                            ))

        return checks

    def _match_catalog_entry(self, srv_name: str, srv_data: Dict[str, Any]) -> Optional[MCPServerEntry]:
        """Attempts to match a server against catalog by name or package argument."""
        # Exact name match
        normalized = srv_name.lower()
        if normalized in self.catalog:
            return self.catalog[normalized]

        # Argument match (e.g. "@modelcontextprotocol/server-github")
        args = srv_data.get("args", [])
        if isinstance(args, list):
            args_str = " ".join(str(a) for a in args)
            for entry in self.catalog.values():
                if entry.name in args_str or (entry.publisher and entry.publisher in args_str):
                    return entry

        return None
