"""Memory adapters to convert between Streamlit session state and message lists."""

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage


def history_to_messages(history: list[dict]) -> list[BaseMessage]:
    """Convert Streamlit conversation history to LangChain BaseMessage list.

    Args:
        history: List of messages in format [{"role": "user"/"assistant", "content": "..."}]

    Returns:
        List of HumanMessage or AIMessage objects
    """
    messages = []
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
    return messages


def messages_to_history(messages: list[BaseMessage]) -> list[dict]:
    """Convert LangChain BaseMessage list back to Streamlit history format.

    Args:
        messages: List of HumanMessage or AIMessage objects

    Returns:
        List of messages in format [{"role": "user"/"assistant", "content": "..."}]
    """
    history = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            history.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            history.append({"role": "assistant", "content": msg.content})
    return history
