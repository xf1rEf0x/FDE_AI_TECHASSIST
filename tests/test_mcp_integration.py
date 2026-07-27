"""Tests for MCP (Tavily) integration."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.mcp_integration import MCPIntegration


def _make_fake_client(tools):
    fake_client = MagicMock()
    fake_client.get_tools = AsyncMock(return_value=tools)
    return fake_client


def _make_fake_tool(name, result=None, side_effect=None):
    tool = MagicMock()
    tool.name = name
    tool.ainvoke = AsyncMock(return_value=result, side_effect=side_effect)
    return tool


def test_init_raises_without_api_key(monkeypatch):
    """Test that MCPIntegration requires TAVILY_API to be set."""
    monkeypatch.delenv("TAVILY_API", raising=False)
    with pytest.raises(ValueError):
        MCPIntegration()


def test_init_loads_tools_from_mcp_client(monkeypatch):
    """Test that tools returned by the MCP client are indexed by name."""
    monkeypatch.setenv("TAVILY_API", "test-key")
    fake_tool = _make_fake_tool("tavily_search", result=[])
    with patch(
        "src.mcp_integration.MultiServerMCPClient",
        return_value=_make_fake_client([fake_tool]),
    ):
        integration = MCPIntegration()

    assert "tavily_search" in integration.tools


def test_get_service_status_parses_mcp_content_blocks(monkeypatch):
    """Test that the MCP tool's content-block response is parsed into structured results."""
    monkeypatch.setenv("TAVILY_API", "test-key")
    mcp_response = [
        {
            "type": "text",
            "text": json.dumps(
                {
                    "results": [
                        {
                            "title": "AWS Status",
                            "content": "All systems operational.",
                            "url": "https://status.aws.amazon.com",
                        }
                    ]
                }
            ),
        }
    ]
    fake_tool = _make_fake_tool("tavily_search", result=mcp_response)
    with patch(
        "src.mcp_integration.MultiServerMCPClient",
        return_value=_make_fake_client([fake_tool]),
    ):
        integration = MCPIntegration()
        result = integration.get_service_status("aws")

    assert result["service"] == "aws"
    assert result["results"][0]["title"] == "AWS Status"
    assert result["results"][0]["url"] == "https://status.aws.amazon.com"
    assert result["source"] == "Tavily MCP Search"


def test_get_service_status_restricts_to_trusted_domains(monkeypatch):
    """Test that the search is restricted to the service's official domain(s)."""
    monkeypatch.setenv("TAVILY_API", "test-key")
    fake_tool = _make_fake_tool("tavily_search", result=[])
    with patch(
        "src.mcp_integration.MultiServerMCPClient",
        return_value=_make_fake_client([fake_tool]),
    ):
        integration = MCPIntegration()
        integration.get_service_status("aws")

    call_args = fake_tool.ainvoke.call_args[0][0]
    assert call_args["include_domains"] == ["status.aws.amazon.com", "health.aws.amazon.com"]


def test_get_service_status_no_results_returns_empty_list(monkeypatch):
    """Test that an empty results list is returned as-is (UI decides how to present it)."""
    monkeypatch.setenv("TAVILY_API", "test-key")
    mcp_response = [{"type": "text", "text": json.dumps({"results": []})}]
    fake_tool = _make_fake_tool("tavily_search", result=mcp_response)
    with patch(
        "src.mcp_integration.MultiServerMCPClient",
        return_value=_make_fake_client([fake_tool]),
    ):
        integration = MCPIntegration()
        result = integration.get_service_status("gcp")

    assert result["results"] == []
    assert result["fallback_url"] == "https://status.cloud.google.com/summary"


def test_get_service_status_handles_tool_error(monkeypatch):
    """Test that a tool invocation error is surfaced as an error dict."""
    monkeypatch.setenv("TAVILY_API", "test-key")
    fake_tool = _make_fake_tool("tavily_search", side_effect=RuntimeError("boom"))
    with patch(
        "src.mcp_integration.MultiServerMCPClient",
        return_value=_make_fake_client([fake_tool]),
    ):
        integration = MCPIntegration()
        result = integration.get_service_status("azure")

    assert "error" in result


def test_get_service_status_rejects_unknown_service(monkeypatch):
    """Test that an unrecognized service name returns an error instead of a bad query."""
    monkeypatch.setenv("TAVILY_API", "test-key")
    fake_tool = _make_fake_tool("tavily_search", result=[])
    with patch(
        "src.mcp_integration.MultiServerMCPClient",
        return_value=_make_fake_client([fake_tool]),
    ):
        integration = MCPIntegration()
        result = integration.get_service_status("dropbox")

    assert "error" in result
