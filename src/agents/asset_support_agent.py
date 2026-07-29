# src/agents/asset_support_agent.py
"""Asset & Support Agent: searches assets, checks warranty, and creates tickets."""

from langchain_core.tools import tool
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.errors import GraphRecursionError
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.agents.agent_loop import extract_text
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


def _build_graph(llm_with_tools, tools: list, system_prompt: str):
    """Two-node LangGraph loop (agent calls the tool-bound LLM, tools node
    executes any tool calls), mirroring SupervisorAgent._build_graph()."""

    def call_model(state):
        response = llm_with_tools.invoke([SystemMessage(system_prompt)] + state["messages"])
        return {"messages": [response]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", ToolNode(tools))
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
    return graph.compile()


def run_asset_support_agent(
    llm, user_email: str, employee_id: str, is_admin: bool, instruction: str, context: str = ""
) -> str:
    """Run the Asset & Support Agent for one delegated task."""
    tools = _build_tools(user_email, employee_id, is_admin)
    llm_with_tools = llm.bind_tools(tools)
    graph = _build_graph(llm_with_tools, tools, ASSET_SUPPORT_SYSTEM_PROMPT)

    input_messages = [HumanMessage(f"Instruction: {instruction}\n\nContext:\n{context}")]
    last_state = {"messages": input_messages}
    try:
        for last_state in graph.stream(
            {"messages": input_messages},
            config={"recursion_limit": 11, "max_concurrency": 1},
            stream_mode="values",
        ):
            pass
    except GraphRecursionError:
        pass

    final_messages = last_state["messages"]
    last_ai_message = next(
        (m for m in reversed(final_messages) if isinstance(m, AIMessage)), None
    )
    if last_ai_message is not None and not last_ai_message.tool_calls:
        return extract_text(last_ai_message)

    fallback = llm.invoke([SystemMessage(ASSET_SUPPORT_SYSTEM_PROMPT)] + final_messages)
    return extract_text(fallback)
