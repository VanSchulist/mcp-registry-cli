"""Package entrypoint when invoked as `python -m mcp_registry`."""

from __future__ import annotations

import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
