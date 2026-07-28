# src/agents/asset_support_agent.py
"""Asset & Support Agent: searches assets, checks warranty, and creates tickets."""

from langchain_core.tools import tool

from src.agents.agent_loop import run_tool_calling_loop
from src.tools.asset_search_tool import search_employee_assets
from src.tools.warranty_tools import check_asset_warranty
from src.tools.ticket_tools import create_ticket_tool

ASSET_SUPPORT_SYSTEM_PROMPT = """You are the Asset & Support Agent, part of TechAssist \
AI's support workflow. You are given an instruction and context describing the user's \
issue and device.

- Use search_asset to find the employee's device/asset.
- Use check_warranty to determine whether its warranty or license is still active.
- Use create_ticket to create a support ticket.

When reporting warranty status, quote the check_warranty tool's verdict verbatim \
(ACTIVE / EXPIRED / UNKNOWN) rather than inferring or restating status from the date \
yourself.

HARD RULE: only call create_ticket if the instruction explicitly states the user has \
confirmed ticket creation. If the instruction only asks you to look up the asset and/or \
warranty, do NOT call create_ticket under any circumstances.

Respond with a short plain-text summary of what you found or did."""


def _build_tools(user_email: str, employee_id: str, is_admin: bool) -> list:
    @tool
    def search_asset(query: str, asset_type: str = None) -> str:
        """Search for the employee's asset by name, serial number, or type."""
        return search_employee_assets.invoke(
            {"query": query, "asset_type": asset_type, "user_id": employee_id, "is_admin": is_admin}
        )

    @tool
    def check_warranty(query: str) -> str:
        """Check whether an asset's warranty or license is still active."""
        return check_asset_warranty.invoke(
            {"query": query, "user_id": employee_id, "is_admin": is_admin}
        )

    @tool
    def create_ticket(title: str, description: str) -> str:
        """Create a support ticket. Only call when explicitly told the user confirmed."""
        result = create_ticket_tool(user_email, title, description)
        return f"Ticket created: {result['message']} (ID: {result['ticket_id']})"

    return [search_asset, check_warranty, create_ticket]


def run_asset_support_agent(
    llm, user_email: str, employee_id: str, is_admin: bool, instruction: str, context: str = ""
) -> str:
    """Run the Asset & Support Agent for one delegated task."""
    tools = _build_tools(user_email, employee_id, is_admin)
    messages = [("user", f"Instruction: {instruction}\n\nContext:\n{context}")]
    result = run_tool_calling_loop(llm, tools, ASSET_SUPPORT_SYSTEM_PROMPT, messages)
    return result["text"]
