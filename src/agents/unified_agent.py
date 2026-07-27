"""TechAssistAgent: Unified LangChain agent for all IT support operations.

Pure LangChain tool-calling agent (no LangGraph) with ConversationBufferMemory.
Consolidates ticket, software, password, and asset tools with role-based access control.
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.chat_history import InMemoryChatMessageHistory
from src.tools.ticket_tools import (
    create_ticket_tool,
    check_ticket_status_tool,
    list_tickets_tool,
    close_ticket_tool,
)
from src.tools.password_tools import reset_password_tool
from src.tools.software_tools import (
    create_software_request_tool,
    check_request_status_tool,
    list_my_requests_tool,
    list_pending_requests_tool,
    approve_request_tool,
    reject_request_tool,
)
from src.asset_search_tool import search_employee_assets


class TechAssistAgent:
    """
    Unified IT support agent powered by LangChain AgentExecutor.

    Handles ticket management, password resets, software requests, and asset lookup
    with automatic user and role-based access control.
    """

    def __init__(
        self,
        user_email: str,
        user_role: str = "employee",
        temperature: float = 0.0,
        model_name: str = "gemini-3.5-flash-lite",
    ):
        """
        Initialize TechAssistAgent.

        Args:
            user_email: Email of the user (used for access control)
            user_role: Role of the user ("employee" or "admin")
            temperature: Temperature for model responses (default 0.0)
            model_name: Name of the Gemini model to use
        """
        self.user_email = user_email
        self.user_role = user_role
        self.temperature = temperature

        # Initialize Gemini LLM
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
        )

        # Set up conversation memory (InMemoryChatMessageHistory with return_messages=True)
        self.memory = InMemoryChatMessageHistory()

        # Define all tools with user/role scoping
        self.tools = self._define_tools()

        # Bind tools to LLM for tool calling
        self.llm_with_tools = self.llm.bind_tools(self.tools)

    def _define_tools(self) -> list:
        """
        Define all tools scoped to user_email and user_role.

        Returns:
            List of LangChain Tool objects
        """
        user_email = self.user_email
        user_role = self.user_role

        # ===== Ticket Tools =====
        @tool
        def create_ticket(title: str, description: str) -> str:
            """Create a new support ticket for the current user."""
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
            """Reset the current user's password. Confirm with user first."""
            result = reset_password_tool(user_email)
            if result["status"] == "error":
                return f"Error: {result['message']}"
            return (
                f"Password reset successful!\n"
                f"Temporary password: {result['new_password']}\n"
                f"IMPORTANT: Change this password immediately on first login."
            )

        # ===== Software Request Tools =====
        @tool
        def request_software(
            software_name: str, version: str, justification: str
        ) -> str:
            """Request new software installation."""
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

        # ===== Asset Lookup Tool =====
        @tool
        def lookup_assets(query: str, asset_type: str = None) -> str:
            """
            Search for employee assets by name, serial number, or type.

            Args:
                query: Search query (employee name or serial number)
                asset_type: Optional asset type filter (Laptop, Monitor, Printer, Software License)
            """
            # Extract user_id from email if needed (assuming email format has consistent structure)
            # For simplicity, pass email as user_id
            result = search_employee_assets(
                query, asset_type, user_id=user_email, is_admin=(user_role == "admin")
            )
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

            tools.extend(
                [
                    list_pending_software_requests,
                    approve_software_request,
                    reject_software_request,
                ]
            )

        return tools

    def _create_system_prompt(self) -> str:
        """
        Create the system prompt text.

        Returns:
            System prompt string
        """
        return f"""You are TechAssist, a professional IT Support Assistant for TechAssist Solutions.

==== YOUR IDENTITY ====
- User Email: {self.user_email}
- User Role: {self.user_role}

==== YOUR CAPABILITIES ====
All ticket, password, software, and asset operations are automatically scoped to the current user.

TICKET MANAGEMENT:
- create_ticket(title, description): Create a new support ticket
- check_ticket_status(ticket_id): Check status of your ticket
- list_my_tickets(): View all your tickets
- close_ticket(ticket_id): Close a resolved ticket

PASSWORD MANAGEMENT:
- reset_password(): Reset your password
  * IMPORTANT: Confirm with user first before calling
  * User will receive a temporary password to change on first login

SOFTWARE REQUESTS:
- request_software(software_name, version, justification): Request new software
- check_software_request_status(request_id): Check request status
- list_my_software_requests(): View all your requests

ASSET LOOKUP:
- lookup_assets(query, asset_type): Search for employee assets by name, serial, or type
  * query: Employee name or serial number
  * asset_type: Optional filter (Laptop, Monitor, Printer, Software License)

{"ADMIN-ONLY CAPABILITIES:" if self.user_role == "admin" else "UNAVAILABLE (Employee role):"}
{"- list_pending_software_requests(): View all pending requests" if self.user_role == "admin" else "- list_pending_software_requests() - Admin only"}
{"- approve_software_request(request_id, approved_by_name): Approve a request" if self.user_role == "admin" else "- approve_software_request() - Admin only"}
{"- reject_software_request(request_id, reason): Reject a request" if self.user_role == "admin" else "- reject_software_request() - Admin only"}

==== ACCESS CONTROL ====
- All operations are automatically scoped to {self.user_email}
- Employees can ONLY manage their own tickets and requests
- Admins can view and approve software requests from all users
- You enforce these boundaries automatically

==== WORKFLOW GUIDELINES ====

FOR PASSWORD RESETS:
1. Inform user you will reset their password
2. Ask for explicit confirmation
3. Only call reset_password() after confirmation
4. Display temporary password clearly
5. Remind: "Change this password immediately after first login"

FOR SUPPORT TICKETS:
1. Gather issue details: what, when, affected systems
2. Create ticket with clear title and description
3. Provide ticket ID for reference

FOR SOFTWARE REQUESTS:
1. Ask for software name, version preference, and business justification
2. Create the request
3. Explain: "Your request is pending admin approval"

FOR ASSET SEARCHES:
1. Ask what asset info user needs (employee name, serial, asset type)
2. Search and present results clearly
3. Include employee info, asset details, warranty/status

==== TONE AND APPROACH ====
- Professional, helpful, patient
- Explain what you're doing and why
- Confirm actions before destructive operations
- Provide clear confirmation messages
- If user access is denied, explain the reason

Always prioritize user needs while maintaining security and access control."""

    def invoke(self, user_input: str) -> str:
        """
        Run the agent with user input and return response text.

        Args:
            user_input: The user's message/request

        Returns:
            The agent's response as a string
        """
        # Add user message to memory
        self.memory.add_user_message(user_input)

        # Get chat history from memory
        history = self.memory.messages

        # Build messages for the LLM: system prompt + history + current input
        messages = []
        messages.append(("system", self._create_system_prompt()))

        # Add conversation history
        for msg in history[:-1]:  # Exclude the last message which is the current input we just added
            if isinstance(msg, HumanMessage):
                messages.append(("user", msg.content))
            elif isinstance(msg, AIMessage):
                messages.append(("assistant", msg.content))

        # Add current user input
        messages.append(("user", user_input))

        # Get response with tool use
        response = self.llm_with_tools.invoke(messages)

        # Handle tool calls if present
        if hasattr(response, "tool_calls") and response.tool_calls:
            # Process tool calls
            tool_results = []
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_input = tool_call["args"]

                # Find and execute the tool
                for tool in self.tools:
                    if tool.name == tool_name:
                        try:
                            result = tool.invoke(tool_input)
                            tool_results.append((tool_name, result))
                        except Exception as e:
                            tool_results.append((tool_name, f"Error: {str(e)}"))
                        break

            # Build a new response that includes tool results
            tool_context = "\n".join(
                [f"Tool {name} returned: {result}" for name, result in tool_results]
            )

            # Get final response after tool use
            final_messages = messages.copy()
            final_messages.append(
                ("assistant", f"I called tool(s) and got results. Let me process this...")
            )
            final_messages.append(
                ("user", f"Based on these tool results: {tool_context}")
            )

            final_response = self.llm.invoke(final_messages)
            response_text = (
                final_response.content
                if hasattr(final_response, "content")
                else str(final_response)
            )
        else:
            # No tool calls, just return the LLM response
            response_text = (
                response.content if hasattr(response, "content") else str(response)
            )

        # Add assistant response to memory
        self.memory.add_ai_message(response_text)

        return response_text
