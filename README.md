# mcp-registry-cli

<div align="center">

[![PyPI version](https://img.shields.io/badge/pypi-v1.0.0-f59e0b.svg?style=flat-square)](https://pypi.org/project/mcp-registry-cli/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-ea580c.svg?style=flat-square)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-d97706.svg?style=flat-square)](LICENSE)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-0%20external-22c55e.svg?style=flat-square)](pyproject.toml)
[![Ecosystem](https://img.shields.io/badge/existential--cloud-ecosystem-78350f.svg?style=flat-square)](https://www.existentialcloud.ccwu.cc)

**The Zero-Config Community Package Manager & Tool Registry for Model Context Protocol (MCP)**

*Discover, inspect, and install verified MCP servers into `mcp-mesh`, Claude Desktop, and Cursor in seconds.*

[Portal & Docs](https://www.existentialcloud.ccwu.cc) • [MCP Gateway (mcp-mesh)](https://github.com/VanSchulist/mcp-mesh) • [Benchmark Suite (mcp-mesh-eval)](https://github.com/VanSchulist/mcp-mesh-eval)

</div>

---

## 🌟 Why mcp-registry-cli?

The Model Context Protocol (MCP) powers agentic AI workflows across Claude, Cursor, and custom agent runtimes. However, installing and managing MCP servers has been manual and error-prone:
- Finding verified server commands and arguments requires digging through GitHub READMEs.
- Writing raw JSON configuration files manually often leads to syntax errors and broken paths.
- Coordinating identical MCP server configurations between **Claude Desktop**, **Cursor**, and the **mcp-mesh** gateway is repetitive.

`mcp-registry-cli` provides an `npm` / `brew`-like CLI experience specifically built for MCP tools:
1. **Curated & Verified Catalog**: 23 verified production-grade servers across database, developer tools, search, browser automation, and cloud integrations.
2. **Multi-Target Ingestion**: One-click install directly into `mcp_mesh.json`, Claude Desktop (`claude_desktop_config.json`), or Cursor (`.cursor/mcp.json`).
3. **Cross-Client Synchronization**: `mcp-registry sync` automatically imports your existing Claude Desktop tools into `mcp-mesh` without duplicate setup.
4. **Zero External Dependencies**: Pure Python standard library implementation that runs anywhere with no extra bloat.

---

## 🚀 Quickstart

### Instant Execution with `uvx` (No Installation Required)

```bash
# Search available servers
uvx mcp-registry-cli search postgres

# Inspect tools and required environment variables
uvx mcp-registry-cli info github

# Install server into mcp-mesh gateway
uvx mcp-registry-cli add postgres github brave-search
```

### Installation via `pip`

```bash
pip install mcp-registry-cli
```

### Direct Run from Source

```bash
git clone https://github.com/VanSchulist/mcp-registry-cli.git
cd mcp-registry-cli
python main.py search
```

---

## 🛠️ CLI Usage Guide

### 1. Search the Registry

Search through verified community and official servers using keyword matching across server names, descriptions, categories, and tool identifiers:

```bash
# Search by topic or query
mcp-registry search database

# Filter by category
mcp-registry search -c developer-tools

# Filter by runtime (node, python, docker)
mcp-registry search -r python

# List official servers only
mcp-registry search --official
```

### 2. Inspect Server Schemas & Tools

View exported tools, runtimes, command definitions, and environment variables:

```bash
mcp-registry info github
```

Output:
```text
GitHub Official MCP (github) - Official MCP Server
Interact with GitHub issues, pull requests, commits, branches, and code search.

  Category:        developer-tools
  Runtime:         node
  Command:         npx -y @modelcontextprotocol/server-github
  Community Stars: 4200
  Homepage:        https://github.com/modelcontextprotocol/servers/tree/main/src/github

  Exported Tools (6):
    - create_issue
    - create_pull_request
    - search_code
    - get_file_contents
    - list_commits
    - create_branch

  Environment Configuration:
    - GITHUB_PERSONAL_ACCESS_TOKEN [required]: GitHub Personal Access Token with repo scope
```

### 3. Add / Install Servers

Install one or more servers into your desired MCP client configuration:

```bash
# Install to mcp-mesh gateway (default: mcp_mesh.json)
mcp-registry add postgres sqlite

# Install to Claude Desktop (automatically resolves OS path)
mcp-registry add github brave-search --client claude

# Install to Cursor editor
mcp-registry add filesystem git --client cursor

# Pass environment variables directly
mcp-registry add brave-search -e BRAVE_API_KEY=your_key_here

# Dry-run preview without modifying files
mcp-registry add slack --dry-run
```

### 4. List Configured Servers

```bash
# List servers configured in local mcp_mesh.json
mcp-registry list

# List servers configured in Claude Desktop
mcp-registry list --client claude

# List all available servers in the global registry
mcp-registry list --all
```

### 5. Synchronize Client Configurations

Automatically import Claude Desktop servers into `mcp-mesh`:

```bash
mcp-registry sync
```

---

## 📁 Supported Client Targets

| Client Target | Default Path (macOS / Linux / Windows) | Config Key |
| :--- | :--- | :--- |
| `mcp-mesh` | `./mcp_mesh.json` | `servers` |
| `claude` | `~/Library/Application Support/Claude/...` / `%APPDATA%\Claude\...` | `mcpServers` |
| `cursor` | `.cursor/mcp.json` / `.mcp.json` | `mcpServers` |
| `--target <path>` | Custom user-specified path | Auto-detected |

---

## 🏛️ Architecture & Ecosystem

```text
       +---------------------------------------------+
       |             mcp-registry-cli                |
       |  (Curated Catalog & Multi-Client Installer) |
       +---------------------+-----------------------+
                             |
             +---------------+---------------+
             |                               |
             v                               v
   +--------------------+          +--------------------+
   |   Claude Desktop   |          |      Cursor        |
   |   & Anthropic Apps |          |      IDE           |
   +--------------------+          +--------------------+
             |                               |
             +---------------+---------------+
                             |
                             v
       +---------------------------------------------+
       |                  mcp-mesh                   |
       |  (Zero-Loss Context Gateway & Token Mesh)   |
       +---------------------+-----------------------+
                             |
                             v
       +---------------------------------------------+
       |                mcp-mesh-eval                |
       |  (Real-World LLM Benchmark & Token Metrics) |
       +---------------------------------------------+
```

---

## 🧪 Testing

Run the standard library test suite:

```bash
python -m unittest discover tests
```

---

## 📜 License

MIT License © 2026 Van Schulist. Part of the [Existential Cloud](https://www.existentialcloud.ccwu.cc) AI Studio ecosystem.
