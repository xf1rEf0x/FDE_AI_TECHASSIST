"""MCP (Model Context Protocol) integration with LangChain for external services."""

import os
from typing import Dict, Any, List


class MCPIntegration:
    """Initialize and manage MCP tools, particularly Tavily search for service status."""

    def __init__(self):
        """Initialize MCP tools with configured API keys."""
        self.tavily_api_key = os.getenv("TAVILY_API")
        if not self.tavily_api_key:
            raise ValueError("TAVILY_API not found in environment variables")
        self.tools = self._initialize_tools()

    def _initialize_tools(self) -> Dict[str, Any]:
        """Initialize available MCP tools."""
        tools = {}

        if self.tavily_api_key:
            from langchain_tavily import TavilySearchResults
            tools["tavily_search"] = TavilySearchResults(
                api_key=self.tavily_api_key,
                max_results=5
            )

        return tools

    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """
        Query service status using Tavily search.

        Args:
            service_name: Name of service (AWS, GCP, Azure, Google)

        Returns:
            Dictionary with service status information
        """
        if "tavily_search" not in self.tools:
            return {"error": "Tavily search not configured"}

        try:
            tavily_tool = self.tools["tavily_search"]

            # Map service names to their status page URLs
            status_queries = {
                "aws": "AWS status page current incidents problems",
                "gcp": "Google Cloud status page current incidents problems",
                "azure": "Microsoft Azure status page current incidents problems",
                "google": "Google services status page current incidents problems",
            }

            query = status_queries.get(
                service_name.lower(),
                f"{service_name} status page current incidents"
            )

            # Use Tavily to search for current status
            results = tavily_tool.invoke({"query": query})

            # Parse results into readable format
            formatted_items = []
            if isinstance(results, str):
                formatted_items = self._parse_status_text(results)
            elif isinstance(results, list):
                for result in results:
                    if isinstance(result, dict):
                        # Extract title and relevant content
                        title = result.get("title", "")
                        content = result.get("content", "")
                        url = result.get("url", "")

                        item_text = f"**{title}**"
                        if content:
                            # Take first 300 chars of content
                            summary = content[:300].strip()
                            if len(content) > 300:
                                summary += "..."
                            item_text += f"\n\n{summary}"
                        if url:
                            item_text += f"\n\n[View full status]({url})"
                        formatted_items.append(item_text)
                    else:
                        formatted_items.append(str(result))
            else:
                formatted_items = [str(results)]

            return {
                "service": service_name,
                "status": formatted_items if formatted_items else ["No incidents reported"],
                "source": "Tavily Search"
            }

        except Exception as e:
            return {"error": f"Failed to get {service_name} status: {str(e)}"}

    def _parse_status_text(self, text: str) -> List[str]:
        """Parse raw status text into readable items."""
        # Split by common delimiters or return as single item
        if len(text) > 500:
            return [text[:500] + "..."]
        return [text] if text.strip() else ["No status information available"]

    def get_all_services_status(self) -> Dict[str, Any]:
        """Get status for all major cloud services."""
        services = ["aws", "gcp", "azure", "google"]
        results = {}

        for service in services:
            results[service] = self.get_service_status(service)

        return results
