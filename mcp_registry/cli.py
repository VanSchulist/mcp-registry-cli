"""Command-line interface (CLI) for the mcp-registry package manager."""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional

from .catalog import MCPServerEntry
from .client import RegistryClient
from .installer import MCPInstaller, TargetClient


class Style:
    """Terminal ANSI colors and safe formatters."""
    ENABLED = sys.stdout.isatty() and os.name != "nt" or "WT_SESSION" in os.environ or "TERM" in os.environ

    HEADER = "\033[95m" if ENABLED else ""
    BLUE = "\033[94m" if ENABLED else ""
    CYAN = "\033[96m" if ENABLED else ""
    GREEN = "\033[92m" if ENABLED else ""
    YELLOW = "\033[93m" if ENABLED else ""
    RED = "\033[91m" if ENABLED else ""
    DIM = "\033[2m" if ENABLED else ""
    BOLD = "\033[1m" if ENABLED else ""
    RESET = "\033[0m" if ENABLED else ""


def _safe_print(text: str = "") -> None:
    """Safely prints text handling Windows GBK / CP936 terminal encodings."""
    try:
        print(text)
    except UnicodeEncodeError:
        try:
            encoding = sys.stdout.encoding or "utf-8"
            sanitized = text.encode(encoding, errors="replace").decode(encoding)
            print(sanitized)
        except Exception:
            ascii_text = text.encode("ascii", errors="replace").decode("ascii")
            print(ascii_text)


def format_stars(stars: int) -> str:
    """Formats star count cleanly (e.g. 4.2k)."""
    if stars >= 1000:
        return f"{stars / 1000:.1f}k"
    return str(stars)


def print_banner() -> None:
    """Prints the warm terminal banner for mcp-registry."""
    banner = f"""{Style.CYAN}{Style.BOLD}======================================================================
  mcp-registry  |  Community MCP Server Registry & Package Manager
  Existential Cloud Ecosystem  |  Zero External Dependencies
======================================================================{Style.RESET}"""
    _safe_print(banner)


def cmd_search(args: argparse.Namespace) -> int:
    """Handles the 'search' subcommand."""
    client = RegistryClient(custom_catalog_path=args.catalog)
    results = client.search(
        query=args.query or "",
        category=args.category,
        runtime=args.runtime,
        official_only=args.official,
    )

    if not results:
        _safe_print(f"{Style.YELLOW}No MCP servers found matching '{args.query}'.{Style.RESET}")
        return 0

    _safe_print(f"{Style.BOLD}Found {len(results)} MCP server(s):{Style.RESET}\n")
    # Table headers
    header = f"{'NAME':<20} {'CATEGORY':<16} {'RUNTIME':<10} {'STARS':<8} {'DESCRIPTION'}"
    _safe_print(f"{Style.DIM}{header}{Style.RESET}")
    _safe_print(f"{Style.DIM}{'-' * 80}{Style.RESET}")

    for entry in results:
        badge = f"{Style.GREEN}[official]{Style.RESET}" if entry.official else f"{Style.DIM}[community]{Style.RESET}"
        name_str = f"{Style.BOLD}{entry.name}{Style.RESET}"
        cat_str = entry.category
        run_str = entry.runtime
        stars_str = format_stars(entry.stars)
        # Truncate description for table display
        desc = entry.description
        if len(desc) > 50:
            desc = desc[:47] + "..."

        _safe_print(f"{entry.name:<20} {cat_str:<16} {run_str:<10} {stars_str:<8} {desc}")

    _safe_print(f"\n{Style.DIM}Run 'mcp-registry info <name>' for details or 'mcp-registry add <name>' to install.{Style.RESET}")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Handles the 'info' subcommand."""
    client = RegistryClient(custom_catalog_path=args.catalog)
    entry = client.get(args.name)

    if not entry:
        _safe_print(f"{Style.RED}Error: Server '{args.name}' not found in registry.{Style.RESET}")
        return 1

    status = f"{Style.GREEN}Official MCP Server{Style.RESET}" if entry.official else f"{Style.YELLOW}Community Server{Style.RESET}"
    _safe_print(f"\n{Style.BOLD}{entry.display_name} ({entry.name}){Style.RESET} - {status}")
    _safe_print(f"{Style.DIM}{entry.description}{Style.RESET}\n")

    _safe_print(f"  {Style.BOLD}Category:{Style.RESET}      {entry.category}")
    _safe_print(f"  {Style.BOLD}Runtime:{Style.RESET}       {entry.runtime}")
    _safe_print(f"  {Style.BOLD}Command:{Style.RESET}       {entry.command} {' '.join(entry.args)}")
    _safe_print(f"  {Style.BOLD}Community Stars:{Style.RESET} {entry.stars}")
    if entry.homepage:
        _safe_print(f"  {Style.BOLD}Homepage:{Style.RESET}      {entry.homepage}")

    if entry.tools:
        _safe_print(f"\n  {Style.BOLD}Exported Tools ({len(entry.tools)}):{Style.RESET}")
        for t in entry.tools:
            _safe_print(f"    - {Style.CYAN}{t}{Style.RESET}")

    if entry.env:
        _safe_print(f"\n  {Style.BOLD}Environment Configuration:{Style.RESET}")
        for env_k, env_v in entry.env.items():
            req_tag = f"{Style.RED}[required]{Style.RESET}" if env_v.get("required") == "true" else f"{Style.DIM}[optional]{Style.RESET}"
            default_val = f" (default: {env_v.get('default')})" if env_v.get("default") else ""
            desc = env_v.get("description", "")
            _safe_print(f"    - {Style.YELLOW}{env_k}{Style.RESET} {req_tag}{default_val}: {desc}")

    _safe_print(f"\n{Style.DIM}Install to mcp-mesh: mcp-registry add {entry.name}{Style.RESET}")
    _safe_print(f"{Style.DIM}Install to Antigravity: mcp-registry add {entry.name} --client antigravity{Style.RESET}")
    _safe_print(f"{Style.DIM}Install to Claude Desktop: mcp-registry add {entry.name} --client claude{Style.RESET}")
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    """Handles 'install' and 'add' subcommands."""
    client = RegistryClient(custom_catalog_path=args.catalog)
    installer = MCPInstaller(target_type=args.client, custom_path=args.target)

    # Parse environment overrides if passed via CLI (-e KEY=VAL)
    env_overrides = {}
    if args.env:
        for item in args.env:
            if "=" in item:
                k, v = item.split("=", 1)
                env_overrides[k.strip()] = v.strip()

    success_count = 0
    for name in args.names:
        entry = client.get(name)
        if not entry:
            _safe_print(f"{Style.RED}[!] Server '{name}' not found in registry catalog.{Style.RESET}")
            continue

        _safe_print(f"[*] Configuring '{entry.name}' for client '{installer.target_type}' ({installer.config_path})...")
        _safe_print(f"    Command: {entry.command} {' '.join(entry.args)}")
        if entry.official:
            _safe_print(f"    {Style.DIM}[Verified Publisher] {entry.publisher or 'Official'} (v{entry.version or 'pinned'}){Style.RESET}")
        else:
            _safe_print(f"    {Style.YELLOW}[Supply Chain Notice] '{entry.name}' is a community-contributed server. Verify code before executing in production.{Style.RESET}")

        # Check required env vars
        missing_required = []
        for env_k, env_v in entry.env.items():
            if env_v.get("required") == "true" and env_k not in env_overrides:
                # Check OS environment
                if env_k in os.environ:
                    env_overrides[env_k] = os.environ[env_k]
                else:
                    missing_required.append(env_k)

        if missing_required:
            _safe_print(f"    {Style.YELLOW}[Warning] Missing required environment variables: {', '.join(missing_required)}{Style.RESET}")
            _safe_print(f"    {Style.DIM}You can supply them using --env {missing_required[0]}=<VALUE> or set in environment.{Style.RESET}")

        ok, msg = installer.install(
            entry,
            env_overrides=env_overrides,
            dry_run=args.dry_run,
            backup=not args.no_backup,
        )

        if ok:
            _safe_print(f"    {Style.GREEN}[+] {msg}{Style.RESET}")
            success_count += 1
        else:
            _safe_print(f"    {Style.RED}[!] {msg}{Style.RESET}")

    return 0 if success_count == len(args.names) else 1


def cmd_uninstall(args: argparse.Namespace) -> int:
    """Handles 'uninstall' and 'remove' subcommands."""
    installer = MCPInstaller(target_type=args.client, custom_path=args.target)
    success_count = 0

    for name in args.names:
        ok, msg = installer.uninstall(name, backup=not args.no_backup)
        if ok:
            _safe_print(f"{Style.GREEN}[+] {msg}{Style.RESET}")
            success_count += 1
        else:
            _safe_print(f"{Style.RED}[!] {msg}{Style.RESET}")

    return 0 if success_count == len(args.names) else 1


def cmd_list(args: argparse.Namespace) -> int:
    """Handles 'list' and 'ls' subcommands."""
    if args.all:
        client = RegistryClient(custom_catalog_path=args.catalog)
        entries = client.list_all()
        _safe_print(f"{Style.BOLD}All Available MCP Registry Servers ({len(entries)}):{Style.RESET}\n")
        header = f"{'NAME':<20} {'CATEGORY':<16} {'RUNTIME':<10} {'STARS':<8} {'TOOLS'}"
        _safe_print(f"{Style.DIM}{header}{Style.RESET}")
        _safe_print(f"{Style.DIM}{'-' * 75}{Style.RESET}")
        for e in entries:
            _safe_print(f"{e.name:<20} {e.category:<16} {e.runtime:<10} {format_stars(e.stars):<8} {len(e.tools)} tools")
        return 0

    installer = MCPInstaller(target_type=args.client, custom_path=args.target)
    installed = installer.list_installed()

    _safe_print(f"{Style.BOLD}Installed MCP Servers in {installer.config_path} ({len(installed)}):{Style.RESET}\n")
    if not installed:
        _safe_print(f"{Style.DIM}No servers configured yet. Run 'mcp-registry search' to explore.{Style.RESET}")
        return 0

    for name, cfg in installed.items():
        cmd = cfg.get("command", "")
        args_str = " ".join(cfg.get("args", []))
        _safe_print(f"  - {Style.CYAN}{Style.BOLD}{name}{Style.RESET}: {cmd} {args_str}")

    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    """Handles synchronization between Claude, Antigravity, Cursor, and mcp-mesh configs."""
    mesh_installer = MCPInstaller(target_type=TargetClient.MCP_MESH)
    claude_installer = MCPInstaller(target_type=TargetClient.CLAUDE)
    antigravity_installer = MCPInstaller(target_type=TargetClient.ANTIGRAVITY)

    _safe_print(f"{Style.CYAN}[*] Inspecting client configurations for cross-tool synchronization...{Style.RESET}")
    claude_servers = claude_installer.list_installed()
    antigravity_servers = antigravity_installer.list_installed()
    mesh_servers = mesh_installer.list_installed()

    _safe_print(f"  Claude Desktop servers found: {len(claude_servers)}")
    _safe_print(f"  Antigravity servers found:    {len(antigravity_servers)}")
    _safe_print(f"  mcp-mesh servers found:       {len(mesh_servers)}")

    external_servers = {}
    external_servers.update(claude_servers)
    external_servers.update(antigravity_servers)

    if not external_servers:
        _safe_print(f"{Style.DIM}No external Claude Desktop or Antigravity servers to sync into mcp-mesh.{Style.RESET}")
        return 0

    imported = 0
    config_data = mesh_installer.load_config()
    target_dict = mesh_installer._get_server_dict(config_data)

    for name, s_cfg in external_servers.items():
        if name not in target_dict:
            target_dict[name] = s_cfg
            imported += 1
            _safe_print(f"  {Style.GREEN}[+] Imported '{name}' into mcp_mesh.json{Style.RESET}")

    if imported > 0:
        import json
        with open(mesh_installer.config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)
        _safe_print(f"\n{Style.GREEN}Synchronization complete: {imported} server(s) imported into {mesh_installer.config_path}.{Style.RESET}")
    else:
        _safe_print(f"\n{Style.DIM}All external servers are already present in mcp_mesh.json.{Style.RESET}")

    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        prog="mcp-registry",
        description="The Zero-Config Community Package Manager & Tool Registry for Model Context Protocol.",
    )
    parser.add_argument("--catalog", type=str, help="Path to external custom catalog JSON file", default=None)

    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # Search
    p_search = subparsers.add_parser("search", help="Search the MCP community registry")
    p_search.add_argument("query", nargs="?", default="", help="Keyword query (name, tool, description)")
    p_search.add_argument("-c", "--category", help="Filter by category (e.g. database, developer-tools, search)")
    p_search.add_argument("-r", "--runtime", choices=["node", "python", "docker", "binary"], help="Filter by runtime")
    p_search.add_argument("--official", action="store_true", help="Filter official servers only")

    # Info
    p_info = subparsers.add_parser("info", help="Display full details and schema for an MCP server")
    p_info.add_argument("name", help="Server name (e.g. github, postgres, brave-search)")

    # Install / Add
    p_install = subparsers.add_parser("add", aliases=["install"], help="Add one or more MCP servers to client config")
    p_install.add_argument("names", nargs="+", help="Server names to install")
    p_install.add_argument("--client", choices=[TargetClient.MCP_MESH, TargetClient.CLAUDE, TargetClient.CURSOR, TargetClient.ANTIGRAVITY],
                           default=TargetClient.MCP_MESH, help="Target MCP client (default: mcp-mesh)")
    p_install.add_argument("--target", type=str, help="Explicit target JSON config file path")
    p_install.add_argument("-e", "--env", action="append", help="Environment variables to configure (KEY=VALUE)")
    p_install.add_argument("--dry-run", action="store_true", help="Preview changes without writing to file")
    p_install.add_argument("--no-backup", action="store_true", help="Do not create .bak backup file")

    # Uninstall / Remove
    p_remove = subparsers.add_parser("remove", aliases=["uninstall"], help="Remove one or more MCP servers from config")
    p_remove.add_argument("names", nargs="+", help="Server names to remove")
    p_remove.add_argument("--client", choices=[TargetClient.MCP_MESH, TargetClient.CLAUDE, TargetClient.CURSOR, TargetClient.ANTIGRAVITY],
                          default=TargetClient.MCP_MESH, help="Target MCP client")
    p_remove.add_argument("--target", type=str, help="Explicit target JSON config file path")
    p_remove.add_argument("--no-backup", action="store_true", help="Do not create .bak backup file")

    # List
    p_list = subparsers.add_parser("list", aliases=["ls"], help="List configured MCP servers")
    p_list.add_argument("--client", choices=[TargetClient.MCP_MESH, TargetClient.CLAUDE, TargetClient.CURSOR, TargetClient.ANTIGRAVITY],
                        default=TargetClient.MCP_MESH, help="Target client configuration to inspect")
    p_list.add_argument("--target", type=str, help="Explicit target JSON config file path")
    p_list.add_argument("-a", "--all", action="store_true", help="List all available servers in registry catalog")

    # Sync
    subparsers.add_parser("sync", help="Synchronize Claude Desktop / Antigravity / Cursor servers into mcp-mesh gateway")

    args = parser.parse_args(argv)

    if not args.subcommand:
        print_banner()
        parser.print_help()
        return 0

    if args.subcommand == "search":
        return cmd_search(args)
    elif args.subcommand == "info":
        return cmd_info(args)
    elif args.subcommand in ("add", "install"):
        return cmd_install(args)
    elif args.subcommand in ("remove", "uninstall"):
        return cmd_uninstall(args)
    elif args.subcommand in ("list", "ls"):
        return cmd_list(args)
    elif args.subcommand == "sync":
        return cmd_sync(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
