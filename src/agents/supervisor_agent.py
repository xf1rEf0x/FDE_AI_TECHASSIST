"""SupervisorAgent: orchestrates Request Analysis, Asset & Support, and Notification
agents as tools, alongside all Phase 2 helpdesk tools."""

import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.chat_history import InMemoryChatMessageHistory

from src.agents.unified_agent import build_helpdesk_tools, rag_retriever
from src.agents.agent_loop import run_tool_calling_loop
from src.agents.request_analysis_agent import analyze_request
from src.agents.asset_support_agent import run_asset_support_agent
from src.agents.notification_agent import run_notification_agent


class SupervisorAgent:
    """
    Multi-agent IT support supervisor.

    Wraps the Request Analysis, Asset & Support, and Notification agents as tools
    alongside all Phase 2 helpdesk tools (tickets, password, software, unlock, KB search).
    """

    PROVIDER_LABELS = {"google": "Google Gemini", "huggingface": "HuggingFace"}
    AGENT_TOOL_LABELS = {
        "analyze_support_request": "Request Analysis Agent",
        "asset_and_ticket_support": "Asset & Support Agent",
        "notify_user": "Notification Agent",
    }

    def __init__(
        self,
        user_email: str,
        user_role: str = "employee",
        temperature: float = 0.0,
        model_name: str = None,
        provider: str = "google",
        employee_id: str = None,
    ):
        self.user_email = user_email
        self.user_role = user_role
        self.employee_id = employee_id
        self.temperature = temperature
        self.provider = provider
        self.provider_label = self.PROVIDER_LABELS.get(provider, provider)
        self.agent_name = "TechAssist Supervisor Agent (Multi-Agent)"
        self.last_tools_used = []
        self.last_rag_used = []
        self.last_token_usage = None
        self.last_agents_used = []
        self._on_progress = lambda label: None

        self.llm, self.model_name = self._build_llm(provider, model_name, temperature)
        self.memory = InMemoryChatMessageHistory()
        self.tools = self._define_tools()

    def _build_llm(self, provider: str, model_name: str, temperature: float):
        """Build the chat model for the selected provider. Returns (llm, resolved_model_name)."""
        if provider == "huggingface":
            repo_id = model_name or os.getenv(
                "HUGGINGFACE_MODEL", "mistralai/Mistral-7B-Instruct-v0.2"
            )
            endpoint = HuggingFaceEndpoint(repo_id=repo_id, temperature=temperature or 0.01)
            return ChatHuggingFace(llm=endpoint), repo_id

        if provider != "google":
            raise ValueError(f"Unknown provider: {provider}")

        resolved_model = model_name or "gemini-3.1-flash-lite"
        return ChatGoogleGenerativeAI(model=resolved_model, temperature=temperature), resolved_model

    def _define_tools(self) -> list:
        base_tools = build_helpdesk_tools(self.user_email, self.user_role, self.employee_id, rag_retriever)

        user_email = self.user_email
        employee_id = self.employee_id
        is_admin = self.user_role == "admin"
        llm = self.llm

        @tool
        def analyze_support_request(user_message: str) -> str:
            """Extract issue type, device, and required action from a free-form IT
            support request. Call this first for new device/VPN/hardware issues before
            looking anything up."""
            self._on_progress(self.AGENT_TOOL_LABELS["analyze_support_request"])
            result = analyze_request(llm, user_message)
            self._on_progress("Supervisor Agent")
            return result.model_dump_json()

        @tool
        def asset_and_ticket_support(instruction: str, context: str = "") -> str:
            """Delegate to the Asset & Support Agent to search assets, check warranty,
            or create a support ticket. `instruction` tells it what to do right now
            (e.g. 'look up the asset and check warranty, do not create a ticket yet'
            or 'the user confirmed, create the ticket now'). `context` carries the
            relevant details gathered so far (issue, device, prior findings)."""
            self._on_progress(self.AGENT_TOOL_LABELS["asset_and_ticket_support"])
            result = run_asset_support_agent(llm, user_email, employee_id, is_admin, instruction, context)
            self._on_progress("Supervisor Agent")
            return result

        @tool
        def notify_user(instruction: str, context: str = "") -> str:
            """Delegate to the Notification Agent to present ticket details and ask
            for confirmation, or to generate and save a final support summary.
            `instruction` e.g. 'preview these ticket details and ask for confirmation'
            or 'the user confirmed and the ticket is created, generate the summary'.
            `context` carries the relevant details to present or summarize."""
            self._on_progress(self.AGENT_TOOL_LABELS["notify_user"])
            result = run_notification_agent(llm, user_email, instruction, context)
            self._on_progress("Supervisor Agent")
            return result

        return base_tools + [analyze_support_request, asset_and_ticket_support, notify_user]

    def _create_system_prompt(self) -> str:
        admin_line = (
            "ADMIN-ONLY: list_pending_software_requests, approve_software_request, "
            "reject_software_request, unlock_account, list_password_reset_requests"
            if self.user_role == "admin"
            else "ADMIN-ONLY tools are not available to your role."
        )
        return f"""You are TechAssist, a professional IT Support Assistant for TechAssist \
Solutions, acting as a Supervisor over specialized agents.

==== YOUR IDENTITY ====
- User Email: {self.user_email}
- User Role: {self.user_role}

==== RESPONSE FORMAT ====
Always format your responses using markdown: **bold** for key info, `code` for IDs, \
bullet/numbered lists, ### headers for sections, > for notes, tables for structured data.

==== MULTI-AGENT WORKFLOW (device/VPN/hardware issues) ====
For requests that describe a device problem, possibly needing a ticket and/or a warranty
check (e.g. "my laptop won't connect to VPN, create a ticket and check my warranty"):

0. For technical/connectivity issues (VPN, password/account trouble, connectivity, etc.),
   ALWAYS call search_knowledge_base(query) first. If it returns relevant documentation,
   answer using that information and stop there. Only continue into the steps below if
   the knowledge base doesn't resolve the issue or the user still wants a ticket created.
1. Call analyze_support_request(user_message) to extract issue/device/action.
2. If a ticket may be needed, call asset_and_ticket_support with an instruction to look
   up the asset and check warranty ONLY — do not ask it to create a ticket yet.
3. Call notify_user with an instruction to preview the proposed ticket (issue, device,
   warranty status) and ask the user to confirm. Then STOP and wait for the user's reply
   — do NOT create the ticket in this turn.
4. Only on a later turn, once the user has explicitly confirmed (e.g. "yes", "go ahead"),
   call asset_and_ticket_support again with an instruction stating the user confirmed and
   to create the ticket now, using the issue/device from step 1-2 as context.
5. Then call notify_user with an instruction to generate and save the summary, and present
   the final confirmation (ticket ID + summary) to the user.

HARD RULE: never let a ticket be created in the same turn as its preview. Always wait for
a separate, explicit user confirmation message first.

==== OTHER CAPABILITIES (tools) ====
TICKET MANAGEMENT: create_ticket, check_ticket_status, list_my_tickets, close_ticket
PASSWORD: reset_password (confirm with user first)
SOFTWARE REQUESTS: request_software, check_software_request_status, list_my_software_requests
ASSET LOOKUP: lookup_assets(query, asset_type)
KNOWLEDGE BASE: search_knowledge_base(query)
{admin_line}

For reset_password, create_ticket (direct tool), and request_software: NEVER call the
tool in the same turn where you present its preview. Always show the template first and
wait for a separate follow-up confirmation. Use this template format:
   ### Ticket Preview
   **Title:** ...
   **Description:** ...
   (or, for software requests)
   ### Software Request Preview
   **Software:** ...
   **Version:** ...
   **Justification:** ...

For account unlocks (admin only, unlock_account): clarify the target email first if not
already given, then call the tool once you have it.

==== ACCESS CONTROL ====
All operations are automatically scoped to {self.user_email}. Employees can only manage
their own tickets and requests; admins can view/approve requests from all users.

Always prioritize user needs while maintaining security and access control."""

    def invoke(self, user_input: str, on_progress: callable = None) -> str:
        """Run the supervisor with user input and return the response text.

        Args:
            on_progress: optional callback invoked with a friendly agent name
                (e.g. "Supervisor Agent", "Asset & Support Agent") each time
                work moves to a different agent, for live status display.
        """
        self._on_progress = on_progress or (lambda label: None)
        self._on_progress("Supervisor Agent")

        self.memory.add_user_message(user_input)
        history = self.memory.messages

        messages = []
        for msg in history[:-1]:
            if isinstance(msg, HumanMessage):
                messages.append(("user", msg.content))
            elif isinstance(msg, AIMessage):
                messages.append(("assistant", msg.content))
        messages.append(("user", user_input))

        result = run_tool_calling_loop(
            self.llm, self.tools, self._create_system_prompt(), messages, max_iterations=6
        )
        response_text = result["text"]
        tool_calls_made = result["tool_calls"]

        self.last_tools_used = [
            tc["name"] for tc in tool_calls_made if tc["name"] != "search_knowledge_base"
        ]
        self.last_rag_used = [
            tc["args"].get("query") for tc in tool_calls_made if tc["name"] == "search_knowledge_base"
        ]
        self.last_token_usage = result["token_usage"]

        agents_used = ["Supervisor Agent"]
        for tc in tool_calls_made:
            label = self.AGENT_TOOL_LABELS.get(tc["name"])
            if label and label not in agents_used:
                agents_used.append(label)
        self.last_agents_used = agents_used

        self.memory.add_ai_message(response_text)
        return response_text
