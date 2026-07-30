"""SupervisorAgent: orchestrates Request Analysis, Asset & Support, and Notification
agents as tools, alongside all Phase 2 helpdesk tools."""

import os
from typing import Annotated, NotRequired, TypedDict

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.chat_history import InMemoryChatMessageHistory
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.errors import GraphRecursionError

from src.agents.helpdesk_tools import build_helpdesk_tools, rag_retriever
from src.agents.agent_loop import extract_text, _extract_usage, _sum_usage
from src.agents.request_analysis_agent import analyze_request
from src.agents.asset_support_agent import run_asset_support_agent
from src.agents.notification_agent import run_notification_agent


class SupervisorGraphState(TypedDict):
    """Supervisor graph state: messages plus scratch fields carrying the
    ticket-workflow's issue/device/findings across its dedicated nodes."""

    messages: Annotated[list, add_messages]
    workflow_phase: NotRequired[str]  # "preview" or "confirm"
    workflow_context: NotRequired[str]
    workflow_tool_call_id: NotRequired[str]


class SupervisorAgent:
    """
    Multi-agent IT support supervisor.

    Wraps the Request Analysis, Asset & Support, and Notification agents as tools
    alongside all Phase 2 helpdesk tools (tickets, password, software, unlock, KB search).
    """

    PROVIDER_LABELS = {"google": "Google Gemini", "huggingface": "HuggingFace"}
    AGENT_TOOL_LABELS = {
        "run_ticket_workflow_preview": "Request Analysis Agent → Asset & Support Agent → Notification Agent",
        "run_ticket_workflow_confirm": "Asset & Support Agent → Notification Agent",
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
        self.base_tools, self.workflow_tools = self._define_tools()
        self.tools = self.base_tools + self.workflow_tools
        self.max_iterations = 6
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.graph = self._build_graph()

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

    def _define_tools(self) -> tuple[list, list]:
        """Returns (base_tools, workflow_tools).

        base_tools are executed normally through the graph's `tools` ToolNode.
        workflow_tools (run_ticket_workflow_preview/confirm) are schema-only —
        the LLM sees and calls them like any other tool, but `_route_after_agent`
        intercepts those two names and sends execution to the dedicated
        request_analysis_agent/asset_support_agent/notification_agent nodes
        instead of ToolNode, so Studio renders them as real graph nodes."""
        base_tools = build_helpdesk_tools(self.user_email, self.user_role, self.employee_id, rag_retriever)

        @tool
        def run_ticket_workflow_preview(user_message: str) -> str:
            """Run the support ticket workflow up through the confirmation step:
            analyze the request, look up the asset and check warranty, then present
            a ticket preview and ask the user to confirm. Call this once for new
            device/VPN/hardware issues that may need a ticket. Do not call it again
            once a preview has been shown — wait for the user's explicit
            confirmation and call run_ticket_workflow_confirm instead."""
            raise NotImplementedError("Executed via graph nodes, not ToolNode — see _route_after_agent.")

        @tool
        def run_ticket_workflow_confirm(context: str) -> str:
            """Call this once the user has explicitly confirmed ticket creation
            (e.g. 'yes', 'go ahead'). Creates the ticket and generates the final
            summary. `context` should restate the issue/device/findings from the
            preview step."""
            raise NotImplementedError("Executed via graph nodes, not ToolNode — see _route_after_agent.")

        return base_tools, [run_ticket_workflow_preview, run_ticket_workflow_confirm]

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

==== MULTI-AGENT TICKET WORKFLOW (device/VPN/hardware issues) ====
For requests that describe a device problem, possibly needing a ticket and/or a warranty
check (e.g. "my laptop won't connect to VPN, create a ticket and check my warranty"):

0. For technical/connectivity issues (VPN, password/account trouble, connectivity, etc.),
   ALWAYS call search_knowledge_base(query) first. If it returns relevant documentation,
   answer using that information and stop there. Only continue below if the knowledge
   base doesn't resolve the issue or the user still wants a ticket created.
1. Call run_ticket_workflow_preview(user_message) with the user's original request. It
   runs the Request Analysis, Asset & Support, and Notification agents in sequence and
   returns a ticket preview asking the user to confirm. Present that preview and STOP —
   do not create the ticket in this turn.
2. Only on a later turn, once the user has explicitly confirmed (e.g. "yes", "go ahead"),
   call run_ticket_workflow_confirm(context) with the issue/device/findings from the
   preview as context. It creates the ticket, generates the summary, and returns the
   final confirmation — present that to the user.

HARD RULE: never call run_ticket_workflow_confirm in the same turn as
run_ticket_workflow_preview. Always wait for a separate, explicit user confirmation
message first.

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

    @staticmethod
    def _find_tool_call(message, name):
        return next((tc for tc in (message.tool_calls or []) if tc["name"] == name), None)

    def _build_graph(self):
        """Supervisor graph: an `agent` node (tool-bound LLM) routes to either
        the plain `tools` ToolNode (all Phase 2 helpdesk tools) or, for the
        ticket workflow, a dedicated chain of real nodes — request_analysis_agent
        -> asset_support_agent -> notification_agent — so each specialist agent
        is its own visible node instead of a function call hidden inside a tool.
        """
        system_prompt = self._create_system_prompt()
        llm = self.llm
        user_email = self.user_email
        employee_id = self.employee_id
        is_admin = self.user_role == "admin"

        def call_model(state):
            response = self.llm_with_tools.invoke([SystemMessage(system_prompt)] + state["messages"])
            return {"messages": [response]}

        def route_after_agent(state):
            last = state["messages"][-1]
            if not isinstance(last, AIMessage) or not last.tool_calls:
                return END
            if self._find_tool_call(last, "run_ticket_workflow_preview"):
                return "request_analysis_agent"
            if self._find_tool_call(last, "run_ticket_workflow_confirm"):
                return "asset_support_agent"
            return "tools"

        def request_analysis_node(state):
            tc = self._find_tool_call(state["messages"][-1], "run_ticket_workflow_preview")
            analysis = analyze_request(llm, tc["args"]["user_message"])
            context = f"Issue: {analysis.issue} | Device: {analysis.device} | Action: {analysis.action}"
            return {"workflow_phase": "preview", "workflow_context": context, "workflow_tool_call_id": tc["id"]}

        def asset_support_node(state):
            if state.get("workflow_phase") == "preview":
                context = state["workflow_context"]
                instruction = "Look up the asset and check warranty only. Do not create a ticket yet."
                update = {}
            else:
                tc = self._find_tool_call(state["messages"][-1], "run_ticket_workflow_confirm")
                context = tc["args"]["context"]
                instruction = "The user confirmed. Create the ticket now."
                update = {"workflow_phase": "confirm", "workflow_tool_call_id": tc["id"]}

            result = run_asset_support_agent(llm, user_email, employee_id, is_admin, instruction, context)
            label = "Ticket result" if update else "Findings"
            update["workflow_context"] = f"{context}\n\n{label}: {result}"
            return update

        def notification_node(state):
            preview = state["workflow_phase"] == "preview"
            instruction = (
                "Preview the proposed ticket (issue, device, warranty status) and ask "
                "the user to confirm. Do not create the ticket yet."
                if preview
                else "The ticket has been created and the user confirmed. Generate and save the summary."
            )
            result = run_notification_agent(llm, user_email, instruction, state["workflow_context"])
            tool_message = ToolMessage(content=result, tool_call_id=state["workflow_tool_call_id"])
            return {"messages": [tool_message]}

        graph = StateGraph(SupervisorGraphState)
        graph.add_node("agent", call_model)
        graph.add_node("tools", ToolNode(self.base_tools))
        graph.add_node("request_analysis_agent", request_analysis_node)
        graph.add_node("asset_support_agent", asset_support_node)
        graph.add_node("notification_agent", notification_node)

        graph.set_entry_point("agent")
        graph.add_conditional_edges(
            "agent",
            route_after_agent,
            {
                "request_analysis_agent": "request_analysis_agent",
                "asset_support_agent": "asset_support_agent",
                "tools": "tools",
                END: END,
            },
        )
        graph.add_edge("tools", "agent")
        graph.add_edge("request_analysis_agent", "asset_support_agent")
        graph.add_edge("asset_support_agent", "notification_agent")
        graph.add_edge("notification_agent", "agent")
        return graph.compile()

    def _to_base_messages(self, messages: list) -> list:
        """Convert (role, content) tuples to BaseMessage instances for the graph."""
        converted = []
        for msg in messages:
            if isinstance(msg, tuple):
                role, content = msg
                converted.append(HumanMessage(content) if role == "user" else AIMessage(content))
            else:
                converted.append(msg)
        return converted

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

        input_messages = self._to_base_messages(messages)
        graph_config = {"recursion_limit": 2 * self.max_iterations + 1, "max_concurrency": 1}
        last_state = {"messages": input_messages}
        try:
            # Stream (not invoke) so that if GraphRecursionError fires mid-turn,
            # we still have the last fully-accumulated state (tool calls/results
            # made so far) instead of losing the whole turn — there's no
            # checkpointer to recover partial state from otherwise.
            last_label = "Supervisor Agent"
            for last_state in self.graph.stream(
                {"messages": input_messages}, config=graph_config, stream_mode="values"
            ):
                # Report progress here, on the main thread — not inside the
                # delegation tools themselves, which LangGraph's ToolNode runs
                # on a worker thread lacking Streamlit's session context.
                latest = last_state["messages"][-1]
                label = "Supervisor Agent"
                if isinstance(latest, AIMessage) and latest.tool_calls:
                    delegate_label = next(
                        (
                            self.AGENT_TOOL_LABELS[tc["name"]]
                            for tc in latest.tool_calls
                            if tc["name"] in self.AGENT_TOOL_LABELS
                        ),
                        None,
                    )
                    if delegate_label:
                        label = delegate_label
                if label != last_label:
                    self._on_progress(label)
                    last_label = label
            new_messages = last_state["messages"][len(input_messages):]
        except GraphRecursionError:
            # Iteration cap hit while the model still wanted to call a tool —
            # one more plain (non-tool-bound) call so the model returns
            # natural-language text instead of leaving the turn empty.
            new_messages = last_state["messages"][len(input_messages):]

        tool_calls_made = [
            {"name": tc["name"], "args": tc["args"]}
            for msg in new_messages
            if isinstance(msg, AIMessage)
            for tc in (msg.tool_calls or [])
        ]

        last_ai_message = next(
            (m for m in reversed(new_messages) if isinstance(m, AIMessage)), None
        )
        if last_ai_message is not None and not last_ai_message.tool_calls:
            response_text = extract_text(last_ai_message)
        else:
            # No clean final text (recursion cap, or the graph's last message
            # still carries tool_calls) — force one plain call for a summary.
            fallback = self.llm.invoke([SystemMessage(self._create_system_prompt())] + input_messages + new_messages)
            response_text = extract_text(fallback)

        self.last_tools_used = [
            tc["name"] for tc in tool_calls_made if tc["name"] != "search_knowledge_base"
        ]
        self.last_rag_used = [
            tc["args"].get("query") for tc in tool_calls_made if tc["name"] == "search_knowledge_base"
        ]
        self.last_token_usage = _sum_usage([_extract_usage(m) for m in new_messages if isinstance(m, AIMessage)])

        agents_used = ["Supervisor Agent"]
        for tc in tool_calls_made:
            label = self.AGENT_TOOL_LABELS.get(tc["name"])
            if label and label not in agents_used:
                agents_used.append(label)
        self.last_agents_used = agents_used

        self.memory.add_ai_message(response_text)
        return response_text
