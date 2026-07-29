"""Notification Agent: presents ticket details, asks for confirmation, and saves summaries."""

from langchain_core.tools import tool

from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.errors import GraphRecursionError
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from src.agents.agent_loop import extract_text
from src.tools.summary_tools import generate_summary_tool

NOTIFICATION_SYSTEM_PROMPT = """You are the Notification Agent, part of TechAssist AI's \
support workflow. You are given an instruction and context describing what happened so far.

- If the instruction asks you to preview ticket details and ask for confirmation, write a \
clear preview (issue, device, warranty status, proposed ticket) and end with a question \
asking the user to confirm. Do NOT call generate_summary in this case.
- If the instruction says the user confirmed and/or the ticket has been created, call \
generate_summary(summary, ticket_id) with a concise summary of the interaction, then tell \
the user it has been saved.
"""


def _build_tools(user_email: str) -> list:
    @tool
    def generate_summary(summary: str, ticket_id: str = None) -> str:
        """Save a summary of this support interaction. Only call after the ticket has been created and the user confirmed."""
        result = generate_summary_tool(user_email, summary, ticket_id)
        return result["message"]

    return [generate_summary]


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


def run_notification_agent(llm, user_email: str, instruction: str, context: str = "") -> str:
    """Run the Notification Agent for one delegated task."""
    tools = _build_tools(user_email)
    llm_with_tools = llm.bind_tools(tools)
    graph = _build_graph(llm_with_tools, tools, NOTIFICATION_SYSTEM_PROMPT)

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

    fallback = llm.invoke([SystemMessage(NOTIFICATION_SYSTEM_PROMPT)] + final_messages)
    return extract_text(fallback)
