"""Curated registry catalog of verified official and community Model Context Protocol (MCP) servers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MCPServerEntry:
    """Represents a verified MCP server in the community registry."""
    name: str
    display_name: str
    description: str
    category: str
    runtime: str  # "node", "python", "docker", "binary"
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, Dict[str, str]] = field(default_factory=dict)
    tools: List[str] = field(default_factory=list)
    stars: int = 0
    official: bool = True
    homepage: str = ""

    def to_mcp_config(self, env_overrides: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Converts entry to standard MCP client JSON configuration format."""
        cfg: Dict[str, Any] = {
            "command": self.command,
            "args": list(self.args),
        }
        active_env: Dict[str, str] = {}
        # Apply default placeholders or user overrides
        for k, v in self.env.items():
            if env_overrides and k in env_overrides:
                active_env[k] = env_overrides[k]
            elif v.get("default"):
                active_env[k] = v["default"]
        if active_env:
            cfg["env"] = active_env
        return cfg


# Curated catalog of 32 enterprise & community MCP servers
CATALOG: Dict[str, MCPServerEntry] = {
    # --- Category: Developer Tools & Git ---
    "github": MCPServerEntry(
        name="github",
        display_name="GitHub Official MCP",
        description="Interact with GitHub issues, pull requests, commits, branches, and code search.",
        category="developer-tools",
        runtime="node",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env={
            "GITHUB_PERSONAL_ACCESS_TOKEN": {
                "description": "GitHub Personal Access Token with repo scope",
                "required": "true",
            }
        },
        tools=["create_issue", "create_pull_request", "search_code", "get_file_contents", "list_commits", "create_branch"],
        stars=4200,
        official=True,
        homepage="https://github.com/modelcontextprotocol/servers/tree/main/src/github",
    ),
    "gitlab": MCPServerEntry(
        name="gitlab",
        display_name="GitLab MCP Server",
        description="Manage GitLab projects, merge requests, issues, pipelines, and repository files.",
        category="developer-tools",
        runtime="node",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-gitlab"],
        env={
            "GITLAB_PERSONAL_ACCESS_TOKEN": {"description": "GitLab Personal Access Token", "required": "true"},
            "GITLAB_API_URL": {"description": "GitLab API Base URL", "default": "https://gitlab.com/api/v4"},
        },
        tools=["create_merge_request", "get_project", "list_issues", "trigger_pipeline"],
        stars=1100,
        official=True,
    ),
    "git": MCPServerEntry(
        name="git",
        display_name="Local Git MCP",
        description="Local Git repository inspector: diff, status, log, branches, and commit generation.",
        category="developer-tools",
        runtime="python",
        command="python",
        args=["-m", "mcp_server_git"],
        env={},
        tools=["git_status", "git_diff", "git_log", "git_commit", "git_branch"],
        stars=1800,
        official=True,
    ),
    "filesystem": MCPServerEntry(
        name="filesystem",
        display_name="Local Filesystem MCP",
        description="Secure local filesystem access for reading, writing, and navigating permitted directories.",
        category="developer-tools",
        runtime="node",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "./"],
        env={},
        tools=["read_file", "write_file", "list_directory", "move_file", "search_files", "get_file_info"],
        stars=3600,
        official=True,
    ),
    "docker": MCPServerEntry(
        name="docker",
        display_name="Docker Container MCP",
        description="Supervise, inspect, run, and stream logs from local Docker containers and images.",
        category="developer-tools",
        runtime="node",
        command="npx",
        args=["-y", "docker-mcp-server"],
        env={},
        tools=["list_containers", "inspect_container", "start_container", "stop_container", "get_logs", "list_images"],
        stars=2400,
        official=False,
    ),
    "kubernetes": MCPServerEntry(
        name="kubernetes",
        display_name="Kubernetes Cluster MCP",
        description="Query pods, deployments, namespaces, and cluster health via kubectl or kubeconfig.",
        category="developer-tools",
        runtime="python",
        command="uvx",
        args=["mcp-server-kubernetes"],
        env={
            "KUBECONFIG": {"description": "Path to kubeconfig file", "default": "~/.kube/config"}
        },
        tools=["get_pods", "get_deployments", "get_services", "describe_resource", "get_pod_logs"],
        stars=1500,
        official=False,
    ),
    "sentry": MCPServerEntry(
        name="sentry",
        display_name="Sentry Error Tracking MCP",
        description="Retrieve exception stack traces, issues, and performance alerts from Sentry projects.",
        category="developer-tools",
        runtime="node",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-sentry"],
        env={
            "SENTRY_AUTH_TOKEN": {"description": "Sentry authentication bearer token", "required": "true"},
            "SENTRY_ORG": {"description": "Sentry organization slug", "required": "true"},
        },
        tools=["list_issues", "get_issue_details", "get_latest_event", "resolve_issue"],
        stars=950,
        official=True,
    ),

    # --- Category: Databases & Storage ---
    "postgres": MCPServerEntry(
        name="postgres",
        display_name="PostgreSQL MCP Server",
        description="Read-only query execution, schema inspection, and table metadata for PostgreSQL.",
        category="database",
        runtime="node",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/mydb"],
        env={
            "POSTGRES_URL": {"description": "PostgreSQL connection URI", "required": "true"}
        },
        tools=["query_readonly", "list_tables", "describe_table", "explain_query"],
        stars=3800,
        official=True,
    ),
    "sqlite": MCPServerEntry(
        name="sqlite",
        display_name="SQLite MCP Server",
        description="Query, inspect tables, and analyze local SQLite databases with safe read-only modes.",
        category="database",
        runtime="python",
        command="uvx",
        args=["mcp-server-sqlite", "--db-path", "./data.db"],
        env={},
        tools=["read_query", "list_tables", "describe_table"],
        stars=2900,
        official=True,
    ),
    "mysql": MCPServerEntry(
        name="mysql",
        display_name="MySQL / MariaDB MCP",
        description="Safe SQL query execution, foreign key schema analysis, and row counting for MySQL.",
        category="database",
        runtime="node",
        command="npx",
        args=["-y", "mysql-mcp-server"],
        env={
            "MYSQL_HOST": {"description": "MySQL hostname", "default": "127.0.0.1"},
            "MYSQL_USER": {"description": "Database username", "required": "true"},
            "MYSQL_PASSWORD": {"description": "Database password", "required": "true"},
            "MYSQL_DATABASE": {"description": "Target database name", "required": "true"},
        },
        tools=["execute_query", "list_tables", "describe_table"],
        stars=1200,
        official=False,
    ),
    "redis": MCPServerEntry(
        name="redis",
        display_name="Redis Key-Value MCP",
        description="Inspect keys, query data structures, read TTL, and monitor Redis cache clusters.",
        category="database",
        runtime="node",
        command="npx",
        args=["-y", "redis-mcp-server"],
        env={
            "REDIS_URL": {"description": "Redis connection URL", "default": "redis://127.0.0.1:6379"}
        },
        tools=["get_key", "list_keys", "get_hash", "check_ttl", "get_server_info"],
        stars=1400,
        official=False,
    ),
    "supabase": MCPServerEntry(
        name="supabase",
        display_name="Supabase MCP Server",
        description="Interact with Supabase Postgres, Edge Functions, Auth users, and Storage buckets.",
        category="database",
        runtime="node",
        command="npx",
        args=["-y", "supabase-mcp-server"],
        env={
            "SUPABASE_URL": {"description": "Supabase Project URL", "required": "true"},
            "SUPABASE_SERVICE_KEY": {"description": "Supabase service_role API key", "required": "true"},
        },
        tools=["query_table", "insert_record", "list_storage_files", "get_user_info"],
        stars=2100,
        official=False,
    ),
    "mongodb": MCPServerEntry(
        name="mongodb",
        display_name="MongoDB Document MCP",
        description="Query BSON documents, aggregate pipelines, and list collections in MongoDB Atlas/local.",
        category="database",
        runtime="node",
        command="npx",
        args=["-y", "mongodb-mcp-server"],
        env={
            "MONGODB_URI": {"description": "MongoDB connection string", "required": "true"}
        },
        tools=["find_documents", "aggregate", "list_collections", "count_documents"],
        stars=1600,
        official=False,
    ),

    # --- Category: Web & Browsing ---
    "puppeteer": MCPServerEntry(
        name="puppeteer",
        display_name="Puppeteer Browser MCP",
        description="Headless Chromium automation: navigate pages, click buttons, capture screenshots, and evaluate JS.",
        category="browser",
        runtime="node",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-puppeteer"],
        env={},
        tools=["navigate", "screenshot", "click", "fill", "evaluate_script"],
        stars=3200,
        official=True,
    ),
    "fetch": MCPServerEntry(
        name="fetch",
        display_name="HTTP Fetch & HTML to Markdown MCP",
        description="High-speed web content scraper converting public HTML pages to clean markdown.",
        category="browser",
        runtime="python",
        command="uvx",
        args=["mcp-server-fetch"],
        env={},
        tools=["fetch_url", "fetch_json", "extract_links"],
        stars=2500,
        official=True,
    ),
    "brave-search": MCPServerEntry(
        name="brave-search",
        display_name="Brave Search MCP",
        description="Real-time web search and local POI lookups using Brave Search API.",
        category="search",
        runtime="node",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-brave-search"],
        env={
            "BRAVE_API_KEY": {"description": "Brave Search API Subscription Key", "required": "true"}
        },
        tools=["brave_web_search", "brave_local_search"],
        stars=3100,
        official=True,
    ),

    # --- Category: AI Memory & Context ---
    "memory": MCPServerEntry(
        name="memory",
        display_name="Knowledge Graph Memory MCP",
        description="Persistent associative memory maintaining entities, relations, and observations across sessions.",
        category="storage",
        runtime="node",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-memory"],
        env={},
        tools=["create_entities", "create_relations", "add_observations", "read_graph", "search_nodes"],
        stars=4800,
        official=True,
    ),

    # --- Category: Collaboration & Productivity ---
    "slack": MCPServerEntry(
        name="slack",
        display_name="Slack MCP Server",
        description="Search conversation history, post channel messages, list channels, and reply to threads.",
        category="communication",
        runtime="node",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-slack"],
        env={
            "SLACK_BOT_TOKEN": {"description": "Slack Bot User OAuth Token (xoxb-...)", "required": "true"},
            "SLACK_TEAM_ID": {"description": "Slack Team Workspace ID", "required": "true"},
        },
        tools=["post_message", "list_channels", "get_channel_history", "reply_to_thread"],
        stars=2300,
        official=True,
    ),
    "notion": MCPServerEntry(
        name="notion",
        display_name="Notion Workspace MCP",
        description="Search workspace pages, read database properties, query tables, and append blocks.",
        category="communication",
        runtime="node",
        command="npx",
        args=["-y", "notion-mcp-server"],
        env={
            "NOTION_API_KEY": {"description": "Notion Internal Integration Token", "required": "true"}
        },
        tools=["search_pages", "get_page_content", "query_database", "create_page"],
        stars=1900,
        official=False,
    ),
    "linear": MCPServerEntry(
        name="linear",
        display_name="Linear Issue Tracker MCP",
        description="Read and create Linear engineering issues, cycles, teams, and project milestones.",
        category="communication",
        runtime="node",
        command="npx",
        args=["-y", "linear-mcp-server"],
        env={
            "LINEAR_API_KEY": {"description": "Linear Personal API Key", "required": "true"}
        },
        tools=["list_issues", "create_issue", "update_issue_status", "list_teams"],
        stars=1700,
        official=False,
    ),
    "jira": MCPServerEntry(
        name="jira",
        display_name="Atlassian Jira MCP",
        description="Search Jira Cloud tickets via JQL, update statuses, add comments, and inspect sprints.",
        category="communication",
        runtime="python",
        command="uvx",
        args=["mcp-server-jira"],
        env={
            "JIRA_URL": {"description": "Atlassian Cloud URL (e.g. https://company.atlassian.net)", "required": "true"},
            "JIRA_USERNAME": {"description": "Account email address", "required": "true"},
            "JIRA_API_TOKEN": {"description": "Atlassian API token", "required": "true"},
        },
        tools=["search_jql", "get_ticket", "create_ticket", "add_comment"],
        stars=1300,
        official=False,
    ),

    # --- Category: Cloud Infrastructure ---
    "aws": MCPServerEntry(
        name="aws",
        display_name="AWS Cloud Operations MCP",
        description="Inspect S3 buckets, query CloudWatch logs, list Lambda functions, and check EC2 instances.",
        category="cloud",
        runtime="python",
        command="uvx",
        args=["mcp-server-aws"],
        env={
            "AWS_REGION": {"description": "Target AWS region (e.g. us-east-1)", "default": "us-east-1"},
            "AWS_ACCESS_KEY_ID": {"description": "AWS access key", "required": "false"},
            "AWS_SECRET_ACCESS_KEY": {"description": "AWS secret access key", "required": "false"},
        },
        tools=["s3_list_buckets", "s3_get_object", "cloudwatch_get_logs", "lambda_list_functions"],
        stars=2800,
        official=False,
    ),
    "google-drive": MCPServerEntry(
        name="google-drive",
        display_name="Google Drive & Docs MCP",
        description="Search Google Drive files, extract Docs text, and read Sheet tab ranges.",
        category="cloud",
        runtime="node",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-gdrive"],
        env={
            "GDRIVE_CREDENTIALS": {"description": "Path to service account credentials.json", "required": "true"}
        },
        tools=["search_drive", "read_file", "list_folder_contents"],
        stars=2100,
        official=True,
    ),
}
