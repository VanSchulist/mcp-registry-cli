"""Client for querying and searching the Model Context Protocol (MCP) server registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from .catalog import CATALOG, MCPServerEntry


class RegistryClient:
    """Registry client providing search, filtering, and inspection of MCP servers."""

    def __init__(self, custom_catalog_path: Optional[str | Path] = None) -> None:
        self.catalog: Dict[str, MCPServerEntry] = dict(CATALOG)
        if custom_catalog_path:
            self._load_custom_catalog(custom_catalog_path)

    def _load_custom_catalog(self, path: str | Path) -> None:
        """Loads additional or override servers from an external JSON file."""
        target = Path(path)
        if not target.is_file():
            return
        try:
            with open(target, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, dict):
                        self.catalog[k] = MCPServerEntry(
                            name=k,
                            display_name=v.get("display_name", k),
                            description=v.get("description", ""),
                            category=v.get("category", "community"),
                            runtime=v.get("runtime", "node"),
                            command=v.get("command", "npx"),
                            args=v.get("args", []),
                            env=v.get("env", {}),
                            tools=v.get("tools", []),
                            stars=v.get("stars", 0),
                            official=v.get("official", False),
                            homepage=v.get("homepage", ""),
                        )
        except Exception:
            # Silently fallback to built-in catalog if file is corrupted
            pass

    def get(self, name: str) -> Optional[MCPServerEntry]:
        """Returns the server entry by name (case-insensitive key match)."""
        normalized = name.strip().lower()
        if normalized in self.catalog:
            return self.catalog[normalized]
        for key, entry in self.catalog.items():
            if key.lower() == normalized or entry.name.lower() == normalized:
                return entry
        return None

    def list_all(self, sort_by_stars: bool = True) -> List[MCPServerEntry]:
        """Returns all available MCP servers in the catalog."""
        entries = list(self.catalog.values())
        if sort_by_stars:
            entries.sort(key=lambda x: x.stars, reverse=True)
        return entries

    def list_categories(self) -> List[str]:
        """Returns a sorted list of unique server categories."""
        cats = {entry.category for entry in self.catalog.values()}
        return sorted(cats)

    def search(
        self,
        query: str = "",
        category: Optional[str] = None,
        runtime: Optional[str] = None,
        official_only: bool = False,
    ) -> List[MCPServerEntry]:
        """Searches the registry with keyword matching, category filtering, and scoring.
        
        Scoring ranking:
        1. Exact name match
        2. Name contains query
        3. Tool name exact/partial match
        4. Category match
        5. Description keyword match
        Ties are broken by GitHub star count.
        """
        q = query.strip().lower()
        results_with_score: List[tuple[int, MCPServerEntry]] = []

        for entry in self.catalog.values():
            if category and entry.category.lower() != category.lower():
                continue
            if runtime and entry.runtime.lower() != runtime.lower():
                continue
            if official_only and not entry.official:
                continue

            if not q:
                # No query string: return all filtered entries with base star score
                results_with_score.append((entry.stars, entry))
                continue

            score = 0
            name_lower = entry.name.lower()
            disp_lower = entry.display_name.lower()
            desc_lower = entry.description.lower()

            if name_lower == q:
                score += 10000
            elif name_lower.startswith(q):
                score += 5000
            elif q in name_lower or q in disp_lower:
                score += 2000

            # Tool matching
            for t in entry.tools:
                t_lower = t.lower()
                if t_lower == q:
                    score += 3000
                elif q in t_lower:
                    score += 1000

            # Category matching
            if q in entry.category.lower():
                score += 800

            # Description matching
            if q in desc_lower:
                score += 500

            if score > 0:
                # Add fractional stars to break ties
                score += entry.stars
                results_with_score.append((score, entry))

        results_with_score.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in results_with_score]
