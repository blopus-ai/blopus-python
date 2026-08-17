"""MCP config helper.

Blopus ships a hosted MCP server (streamable-HTTP) at https://mcp.blopus.ai with
``search`` and ``fetch`` tools, gated by the same Bearer auth as the REST API.
:func:`mcp_config` returns the ``mcpServers`` block you drop into a client
(Claude Desktop, Cursor, etc.).
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from . import _common as C


def mcp_config(
    api_key: Optional[str] = None,
    *,
    url: str = C.DEFAULT_MCP_URL,
    server_name: str = "blopus",
) -> Dict[str, Any]:
    """Return the ``mcpServers`` JSON object for the hosted Blopus MCP server."""
    key = C.resolve_api_key(api_key)
    return {
        "mcpServers": {
            server_name: {
                "type": "http",
                "url": url,
                "headers": {"Authorization": f"Bearer {key}"},
            }
        }
    }


def print_mcp_config(api_key: Optional[str] = None, *, url: str = C.DEFAULT_MCP_URL) -> None:
    """Pretty-print the MCP config JSON to stdout."""
    print(json.dumps(mcp_config(api_key, url=url), indent=2))
