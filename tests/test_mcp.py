"""Tests for the MCP config helper."""
from blopus import mcp_config


def test_mcp_config_shape():
    cfg = mcp_config("blp_live_abc")
    assert "mcpServers" in cfg
    server = cfg["mcpServers"]["blopus"]
    assert server["url"] == "https://mcp.blopus.ai"
    assert server["headers"]["Authorization"] == "Bearer blp_live_abc"
