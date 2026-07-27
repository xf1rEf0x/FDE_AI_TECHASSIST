"""MCP (Model Context Protocol) integration with LangChain for external services.

Connects to Tavily's hosted MCP server (rather than the langchain-tavily SDK
wrapper) via langchain-mcp-adapters, and uses its tavily_search tool for
service status lookups — restricted to each provider's own official status
domain(s) so results don't get diluted by third-party aggregators
(Downdetector, StatusGator, etc).
"""

import asyncio
import json
import os
from typing import Any, Dict, List

from langchain_mcp_adapters.client import MultiServerMCPClient

TAVILY_MCP_URL = "https://mcp.tavily.com/mcp/"

# Each service is only searched within its own official status domain(s), and
# carries a direct fallback link for when search turns up nothing.
STATUS_SOURCES = {
    "aws": {
        "label": "AWS",
        "query": "AWS service health dashboard current status incidents",
        "domains": ["status.aws.amazon.com", "health.aws.amazon.com"],
        "fallback_url": "https://health.aws.amazon.com/health/status",
    },
    "gcp": {
        "label": "Google Cloud",
        "query": "Google Cloud status incidents current",
        "domains": ["status.cloud.google.com"],
        "fallback_url": "https://status.cloud.google.com/summary",
    },
    "azure": {
        "label": "Azure",
        "query": "Azure status incidents current",
        "domains": ["azure.status.microsoft", "status.azure.com"],
        "fallback_url": "https://azure.status.microsoft/en-us/status",
    },
    "google": {
        "label": "Google Workspace",
        "query": "Google Workspace apps status dashboard incidents",
        "domains": ["www.google.com"],
        "fallback_url": "https://www.google.com/appsstatus/dashboard",
    },
}


class MCPIntegration:
    """Initialize and manage MCP tools, particularly Tavily search for service status."""

    def __init__(self):
        """Initialize MCP tools with configured API keys."""
        self.tavily_api_key = os.getenv("TAVILY_API")
        if not self.tavily_api_key:
            raise ValueError("TAVILY_API not found in environment variables")
        self.tools = self._initialize_tools()

    def _initialize_tools(self) -> Dict[str, Any]:
        """Connect to the Tavily MCP server and load its tools."""
        client = MultiServerMCPClient({
            "tavily": {
                "url": f"{TAVILY_MCP_URL}?tavilyApiKey={self.tavily_api_key}",
                "transport": "streamable_http",
            }
        })
        mcp_tools = asyncio.run(client.get_tools())
        return {tool.name: tool for tool in mcp_tools}

    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """
        Query service status using the Tavily MCP search tool, restricted to
        the service's own official status domain(s).

        Args:
            service_name: Name of service (aws, gcp, azure, google)

        Returns:
            dict with keys: service, results (list of {title, content, url}),
            domains (trusted domains searched), fallback_url, source
            — or {"error": "..."} on failure
        """
        search_tool = self.tools.get("tavily_search")
        if search_tool is None:
            return {"error": "Tavily search not configured"}

        source = STATUS_SOURCES.get(service_name.lower())
        if source is None:
            return {"error": f"Unknown service: {service_name}"}

        try:
            raw_result = asyncio.run(search_tool.ainvoke({
                "query": source["query"],
                "include_domains": source["domains"],
                "max_results": 4,
            }))
            results = self._extract_search_results(raw_result)

            return {
                "service": service_name,
                "results": results,
                "domains": source["domains"],
                "fallback_url": source["fallback_url"],
                "source": "Tavily MCP Search",
            }

        except Exception as e:
            return {"error": f"Failed to get {service_name} status: {str(e)}"}

    def _extract_search_results(self, raw_result: Any) -> List[dict]:
        """Parse the MCP tool's content-block response into a list of result dicts.

        The Tavily MCP tool returns a list of content blocks (each
        {"type": "text", "text": "<json string>"}), where the JSON string
        contains a "results" list of {url, title, content, score}.
        """
        results = []
        blocks = raw_result if isinstance(raw_result, list) else [raw_result]

        for block in blocks:
            text = block.get("text") if isinstance(block, dict) else block
            if not isinstance(text, str):
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            results.extend(payload.get("results", []))

        return results

    def get_all_services_status(self) -> Dict[str, Any]:
        """Get status for all major cloud services."""
        return {service: self.get_service_status(service) for service in STATUS_SOURCES}
