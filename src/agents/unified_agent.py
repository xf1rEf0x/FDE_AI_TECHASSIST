"""TechAssistAgent: Unified LangChain agent for all IT support operations.

Pure LangChain tool-calling agent (no LangGraph) with ConversationBufferMemory.
Consolidates ticket, software, password, and asset tools with role-based access control.
"""

import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.chat_history import InMemoryChatMessageHistory
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
_rag_retriever = RAGRetriever()


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
        model_name: str = None,
        provider: str = "google",
        employee_id: str = None,
    ):
        """
        Initialize TechAssistAgent.

        Args:
            user_email: Email of the user (used for access control)
            user_role: Role of the user ("employee" or "admin")
            temperature: Temperature for model responses (default 0.0)
            model_name: Name of the model to use (defaults per provider)
            provider: LLM provider, "google" or "huggingface"
            employee_id: Employee ID for asset lookup scoping (e.g. "EMP001")
        """
        self.user_email = user_email
        self.user_role = user_role
        self.employee_id = employee_id
        self.temperature = temperature
        self.provider = provider
        self.provider_label = self.PROVIDER_LABELS.get(provider, provider)
        self.agent_name = "TechAssist Unified Agent (LangChain tool-calling)"
        self.last_tools_used = []
        self.last_rag_used = []
        self.last_token_usage = None

        self.llm, self.model_name = self._build_llm(provider, model_name, temperature)

        # Set up conversation memory (InMemoryChatMessageHistory with return_messages=True)
        self.memory = InMemoryChatMessageHistory()

        # Define all tools with user/role scoping
        self.tools = self._define_tools()

        # Bind tools to LLM for tool calling
        self.llm_with_tools = self.llm.bind_tools(self.tools)

    PROVIDER_LABELS = {"google": "Google Gemini", "huggingface": "HuggingFace"}

    def _build_llm(self, provider: str, model_name: str, temperature: float):
        """Build the chat model for the selected provider. Returns (llm, resolved_model_name)."""
        if provider == "huggingface":
            repo_id = model_name or os.getenv(
                "HUGGINGFACE_MODEL", "HuggingFaceH4/zephyr-7b-beta"
            )
            endpoint = HuggingFaceEndpoint(repo_id=repo_id, temperature=temperature or 0.01)
            return ChatHuggingFace(llm=endpoint), repo_id

        if provider != "google":
            raise ValueError(f"Unknown provider: {provider}")

        resolved_model = model_name or "gemini-3.1-flash-lite"
        return ChatGoogleGenerativeAI(
            model=resolved_model,
            temperature=temperature,
        ), resolved_model

    def _define_tools(self) -> list:
        """
        Define all tools scoped to user_email and user_role.

        Returns:
            List of LangChain Tool objects
        """
        user_email = self.user_email
        user_role = self.user_role
        employee_id = self.employee_id

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
            context = _rag_retriever.format_context(query)
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

    def _extract_text(self, response) -> str:
        """Extract text from LLM response (handles both string and list formats)."""
        if not hasattr(response, "content"):
            return str(response)

        content = response.content
        if isinstance(content, str):
            return content

        # Gemini may return list of content blocks
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    text_parts.append(item["text"])
                elif isinstance(item, str):
                    text_parts.append(item)
                else:
                    text_parts.append(str(item))
            return "".join(text_parts)

        return str(content)

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

==== RESPONSE FORMAT ====
Always format your responses using markdown:
- Use **bold** for important information
- Use `code` for ticket IDs, request IDs, and technical terms
- Use bullet points (- ) for lists
- Use numbered lists (1. ) for steps
- Use ### headers for sections
- Use > for important notes
- Use tables when presenting structured data

==== YOUR CAPABILITIES ====
All ticket, password, software, and asset operations are automatically scoped to the current user.

TICKET MANAGEMENT:
- create_ticket(title, description): Create a new support ticket
- check_ticket_status(ticket_id): Check status of your ticket
- list_my_tickets(): View all your tickets
- close_ticket(ticket_id): Close a resolved ticket

PASSWORD MANAGEMENT:
- reset_password(): Raise a password reset request (does not change the password directly)
  * IMPORTANT: Confirm with user first before calling
  * Request is queued for IT to fulfill, similar to a support ticket

SOFTWARE REQUESTS:
- request_software(software_name, version, justification): Request new software
- check_software_request_status(request_id): Check request status
- list_my_software_requests(): View all your requests

ASSET LOOKUP:
- lookup_assets(query, asset_type): Search for employee assets by name, serial, or type
  * query: Employee name or serial number
  * asset_type: Optional filter (Laptop, Monitor, Printer, Software License)

KNOWLEDGE BASE:
- search_knowledge_base(query): Search internal IT documentation (VPN, password/account
  troubleshooting, etc.) for a documented answer

{"ADMIN-ONLY CAPABILITIES:" if self.user_role == "admin" else "UNAVAILABLE (Employee role):"}
{"- list_pending_software_requests(): View all pending requests" if self.user_role == "admin" else "- list_pending_software_requests() - Admin only"}
{"- approve_software_request(request_id, approved_by_name): Approve a request" if self.user_role == "admin" else "- approve_software_request() - Admin only"}
{"- reject_software_request(request_id, reason): Reject a request" if self.user_role == "admin" else "- reject_software_request() - Admin only"}
{"- unlock_account(target_email): Unlock a user's locked account" if self.user_role == "admin" else "- unlock_account() - Admin only"}
{"- list_password_reset_requests(): View all pending password reset requests" if self.user_role == "admin" else "- list_password_reset_requests() - Admin only"}

==== ACCESS CONTROL ====
- All operations are automatically scoped to {self.user_email}
- Employees can ONLY manage their own tickets and requests
- Admins can view and approve software requests from all users
- You enforce these boundaries automatically

==== WORKFLOW GUIDELINES ====

HARD RULE: For reset_password, create_ticket, and request_software, NEVER call the
tool in the same turn where you present the template — even if the user's very
first message already contains every required detail or explicitly says "please do
X" / "go ahead". A direct or detailed request is NOT the same as confirming a
preview. Always show the template first and wait for a separate follow-up message
where the user agrees, then call the tool on that later turn.

FOR PASSWORD RESETS:
1. Present a template preview: "I'll raise a password reset request for **{{email}}**. Confirm?"
2. Wait for explicit user agreement ("yes", "confirm", etc.)
3. If user rejects or wants changes, ask a clarifying question and present a revised template — do NOT call reset_password() yet
4. Only call reset_password() after the user confirms the template
5. Provide the request ID and explain: "IT will process this request shortly"

FOR TECHNICAL ISSUES (VPN, password/account trouble, connectivity, etc.):
1. ALWAYS call search_knowledge_base(query) first before answering
2. If it returns relevant documentation, answer using that information
3. If it returns "No relevant documentation found", tell the user you couldn't
   find a documented answer and ask if they'd like a support ticket created
4. Only proceed to create a ticket if the user agrees

FOR SUPPORT TICKETS:
1. Gather issue details: what, when, affected systems
2. Present a template preview (do NOT call create_ticket yet):
   ### Ticket Preview
   **Title:** ...
   **Description:** ...
   Ask: "Does this look right? Shall I create this ticket?"
3. If user confirms, call create_ticket(title, description) and provide the ticket ID
4. If user rejects or wants changes, ask a clarifying question and present a revised template — repeat until confirmed

FOR SOFTWARE REQUESTS:
1. Ask for software name, version preference, and business justification
2. Present a template preview (do NOT call request_software yet):
   ### Software Request Preview
   **Software:** ...
   **Version:** ...
   **Justification:** ...
   Ask: "Does this look right? Shall I submit this request?"
3. If user confirms, call request_software(...) and explain: "Your request is pending admin approval"
4. If user rejects or wants changes, ask a clarifying question and present a revised template — repeat until confirmed

FOR ACCOUNT UNLOCKS (admin only):
1. Clarify which user's account needs unlocking — ask for the email if not given
2. Once you have the target email, call unlock_account(target_email)
3. Confirm to the admin that the account has been unlocked

FOR ASSET SEARCHES:
1. Ask what asset info user needs (employee name, serial, asset type)
2. Search and present results clearly
3. Include employee info, asset details, warranty/status

==== TONE AND APPROACH ====
- Professional, helpful, patient
- Explain what you're doing and why
- Confirm actions before destructive operations (tickets, software requests, password resets) by showing a template preview and waiting for explicit agreement before calling the tool
- For account unlocks, clarify the target account then act — no template preview needed
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

        # Track which tools/knowledge base this turn used (for display in the UI)
        self.last_tools_used = []
        self.last_rag_used = []
        token_usages = [self._extract_usage(response)]

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

            # search_knowledge_base is surfaced as its own "RAG" component in
            # the UI rather than lumped in with regular tools.
            self.last_tools_used = [
                name for name, _ in tool_results if name != "search_knowledge_base"
            ]
            self.last_rag_used = [
                call["args"]["query"]
                for call, (name, result) in zip(response.tool_calls, tool_results)
                if name == "search_knowledge_base" and result != "No relevant documentation found."
            ]

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
            token_usages.append(self._extract_usage(final_response))
            response_text = self._extract_text(final_response)
        else:
            # No tool calls, just return the LLM response
            response_text = self._extract_text(response)

        self.last_token_usage = self._sum_usage(token_usages)

        # Add assistant response to memory
        self.memory.add_ai_message(response_text)

        return response_text

    def _extract_usage(self, response) -> dict:
        """Pull token usage out of an LLM response, if the provider reports it."""
        usage = getattr(response, "usage_metadata", None)
        if not usage:
            return None
        return {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        }

    def _sum_usage(self, usages: list) -> dict:
        """Sum token usage across one or more LLM calls in this turn."""
        usages = [u for u in usages if u]
        if not usages:
            return None
        return {
            key: sum(u[key] for u in usages)
            for key in ("input_tokens", "output_tokens", "total_tokens")
        }
