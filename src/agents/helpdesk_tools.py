"""Helpdesk tool definitions, shared by the Supervisor's Phase 2 tools.

Defines `build_helpdesk_tools`, the shared tool-definition function used by
`SupervisorAgent` (`src/agents/supervisor_agent.py`) to build its Phase 2 tools
(tickets, password, software, asset lookup, knowledge base).
"""

from langchain.tools import tool
from src.tools.ticket_tools import (
    create_ticket_tool,
    check_ticket_status_tool,
    list_tickets_tool,
    close_ticket_tool,
)
from src.tools.password_tools import reset_password_tool, list_pending_password_reset_requests_tool
from src.tools.account_tools import unlock_account_tool
from src.tools.software_tools import (
    create_software_request_tool,
    check_request_status_tool,
    list_my_requests_tool,
    list_pending_requests_tool,
    approve_request_tool,
    reject_request_tool,
)
from src.tools.asset_search_tool import search_employee_assets
from src.rag import RAGRetriever

# Loaded once at import time and shared across agent instances/sessions —
# parsing the PDFs on every login/provider-switch would be wasted work.
rag_retriever = RAGRetriever()


def build_helpdesk_tools(
    user_email: str, user_role: str, employee_id: str, rag_retriever: RAGRetriever
) -> list:
    """
    Define all helpdesk tools scoped to user_email and user_role.

    Returns:
        List of LangChain Tool objects
    """
    # ===== Ticket Tools =====
    @tool
    def create_ticket(title: str, description: str) -> str:
        """Create a new support ticket for the current user. Only call after the user has confirmed the previewed template."""
        result = create_ticket_tool(user_email, title, description)
        return f"Ticket created: {result['message']} (ID: {result['ticket_id']})"

    @tool
    def check_ticket_status(ticket_id: str) -> str:
        """Check the status of a support ticket owned by the current user."""
        result = check_ticket_status_tool(user_email, ticket_id)
        if result["status"] == "error":
            return f"Error: {result['message']}"
        ticket = result["ticket"]
        return (
            f"Ticket {ticket['ticket_id']}: {ticket['title']}\n"
            f"Status: {ticket['status']}\n"
            f"Created: {ticket['created_at']}\n"
            f"Description: {ticket['description']}"
        )

    @tool
    def list_my_tickets() -> str:
        """List all support tickets owned by the current user."""
        result = list_tickets_tool(user_email)
        tickets = result["tickets"]
        if not tickets:
            return "No tickets found."
        ticket_list = "\n".join(
            [
                f"- {t['ticket_id']}: {t['title']} ({t['status']})"
                for t in tickets
            ]
        )
        return f"Your tickets:\n{ticket_list}"

    @tool
    def close_ticket(ticket_id: str) -> str:
        """Close a support ticket owned by the current user."""
        result = close_ticket_tool(user_email, ticket_id)
        if result["status"] == "error":
            return f"Error: {result['message']}"
        return f"Ticket {ticket_id} closed successfully."

    # ===== Password Tool =====
    @tool
    def reset_password() -> str:
        """Raise a password reset request for the current user (does not change the password directly). Only call after the user has confirmed the previewed template."""
        result = reset_password_tool(user_email)
        if result["status"] == "error":
            return f"Error: {result['message']}"
        return f"Password reset request raised: {result['message']} (Request ID: {result['request_id']})"

    # ===== Software Request Tools =====
    @tool
    def request_software(
        software_name: str, version: str, justification: str
    ) -> str:
        """Request new software installation. Only call after the user has confirmed the previewed template."""
        result = create_software_request_tool(
            user_email, software_name, version, justification
        )
        return f"Software request created: {result['message']}"

    @tool
    def check_software_request_status(request_id: str) -> str:
        """Check the status of a software request owned by the current user."""
        result = check_request_status_tool(user_email, request_id)
        if result["status"] == "error":
            return f"Error: {result['message']}"
        req = result["request"]
        return (
            f"Software Request {req['request_id']}: {req['software_name']}\n"
            f"Version: {req['version']}\n"
            f"Status: {req['status']}\n"
            f"Requested: {req['request_date']}\n"
            f"Justification: {req['justification']}\n"
            f"Approved by: {req['approved_by'] or 'Pending'}"
        )

    @tool
    def list_my_software_requests() -> str:
        """List all software requests owned by the current user."""
        result = list_my_requests_tool(user_email)
        requests = result["requests"]
        if not requests:
            return "No software requests found."
        req_list = "\n".join(
            [
                f"- {r['request_id']}: {r['software_name']} v{r['version']} ({r['status']})"
                for r in requests
            ]
        )
        return f"Your software requests:\n{req_list}"

    # ===== Knowledge Base (RAG) Tool =====
    @tool
    def search_knowledge_base(query: str) -> str:
        """Search internal IT documentation (VPN, password/account troubleshooting, etc.) for an answer."""
        context = rag_retriever.format_context(query)
        return context or "No relevant documentation found."

    # ===== Asset Lookup Tool =====
    @tool
    def lookup_assets(query: str, asset_type: str = None) -> str:
        """
        Search for employee assets by name, serial number, or type.

        Args:
            query: Search query (employee name or serial number)
            asset_type: Optional asset type filter (Laptop, Monitor, Printer, Software License)
        """
        result = search_employee_assets.invoke({
            "query": query,
            "asset_type": asset_type,
            "user_id": employee_id,
            "is_admin": user_role == "admin",
        })
        return result

    # Build base tools list
    tools = [
        create_ticket,
        check_ticket_status,
        list_my_tickets,
        close_ticket,
        reset_password,
        request_software,
        check_software_request_status,
        list_my_software_requests,
        search_knowledge_base,
        lookup_assets,
    ]

    # Admin-only tools
    if user_role == "admin":

        @tool
        def list_pending_software_requests() -> str:
            """List all pending software requests (admin only)."""
            result = list_pending_requests_tool()
            requests = result["requests"]
            if not requests:
                return "No pending software requests."
            req_list = "\n".join(
                [
                    f"- {r['request_id']}: {r['software_name']} v{r['version']} "
                    f"(requested by {r['requester_email']} on {r['request_date']})"
                    for r in requests
                ]
            )
            return f"Pending software requests:\n{req_list}"

        @tool
        def approve_software_request(
            request_id: str, approved_by_name: str
        ) -> str:
            """Approve a pending software request (admin only)."""
            result = approve_request_tool(
                request_id, user_email, approved_by_name
            )
            if result["status"] == "error":
                return f"Error: {result['message']}"
            return f"Request {request_id} approved successfully."

        @tool
        def reject_software_request(request_id: str, reason: str) -> str:
            """Reject a pending software request (admin only)."""
            result = reject_request_tool(request_id, user_email, reason)
            if result["status"] == "error":
                return f"Error: {result['message']}"
            return f"Request {request_id} rejected. Reason: {reason}"

        @tool
        def unlock_account(target_email: str) -> str:
            """Unlock a user's account so they can log in again (admin only). Clarify the target email first if not already given."""
            result = unlock_account_tool(target_email)
            if result["status"] == "error":
                return f"Error: {result['message']}"
            return result["message"]

        @tool
        def list_password_reset_requests() -> str:
            """List all pending password reset requests (admin only)."""
            result = list_pending_password_reset_requests_tool()
            requests = result["requests"]
            if not requests:
                return "No pending password reset requests."
            req_list = "\n".join(
                [
                    f"- {r['request_id']}: {r['user_email']} (requested on {r['requested_at']})"
                    for r in requests
                ]
            )
            return f"Pending password reset requests:\n{req_list}"

        tools.extend(
            [
                list_pending_software_requests,
                approve_software_request,
                reject_software_request,
                unlock_account,
                list_password_reset_requests,
            ]
        )

    return tools

