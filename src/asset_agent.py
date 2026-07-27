"""AI Agent for Employee Assets search using LangGraph."""

import re
from typing import Optional
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from src.langchain_integration import create_langchain_model
from src.asset_search_tool import search_employee_assets as _search_employee_assets


def create_asset_search_agent(temperature: float = 0.7, user_name: str = None, user_id: str = None, is_admin: bool = False):
    """Create an AI agent for searching employee assets.

    The agent helps users find their assigned assets by answering natural language
    queries about laptops, monitors, software licenses, and printers.

    Args:
        temperature: Model temperature for response generation (0.0 - 2.0)
        user_name: Optional current user's name for personalized search
        user_id: Optional current user's employee ID for access control
        is_admin: Whether current user is admin (bypasses access control)

    Returns:
        LangGraph agent configured with asset search tool
    """
    model = create_langchain_model(temperature)

    # Create a bounded tool that captures user_id and is_admin from closure
    @tool
    def search_employee_assets(query: str, asset_type: Optional[str] = None) -> str:
        """Search for employee assets by name, serial number, or type.

        This tool searches across employee assets in the system. You can:
        - Search by employee name (e.g., "Alice Johnson")
        - Search by serial number or license key (e.g., "C02XQ8NWLXJX")
        - Filter by asset type (e.g., "Laptop", "Monitor", "Software License", "Printer")

        Args:
            query: Search query (employee name or serial number)
            asset_type: Optional asset type to filter by

        Returns:
            Formatted string with search results
        """
        # Call the underlying search with user access control
        return _search_employee_assets(
            query=query,
            asset_type=asset_type,
            user_id=user_id,  # Captured from closure
            is_admin=is_admin  # Captured from closure
        )

    tools = [search_employee_assets]

    user_context = f"The current user's name is: {user_name}\n" if user_name else ""
    access_note = "You are an admin and can see all employees' assets." if is_admin else "Only show assets for the current user if you have their employee ID."

    system_prompt = f"""You are a helpful IT Support Assistant specializing in employee asset management.
Your role is to help employees find information about their assigned hardware and software assets.

{user_context}

{access_note}

RESPOND ONLY WITH THE FINAL ANSWER - do not show your thinking process, reasoning, or internal thoughts.

When a user asks about assets:
1. If they say "me", "my", "mine" or "assigned to me" - search using the current user's name if available
2. Otherwise, use the search_employee_assets tool to find assets by name, serial number, or type
3. The tool can search by:
   - Employee name (e.g., "Alice", "Bob Smith")
   - Serial number or license key (e.g., "C02XQ8NWLXJX")
   - Asset type (e.g., "Laptop", "Monitor", "Software License", "Printer")

Guidelines:
1. Be helpful and professional
2. If user says "me" but you don't have their name in context, politely ask for their name
3. Provide complete asset details when found
4. If an asset is not found, suggest alternative search terms
5. Provide warranty/expiry information when relevant
6. Keep responses concise and focused on the asset information"""

    agent = create_react_agent(model, tools, prompt=system_prompt)
    return agent


def _clean_response(text: str) -> str:
    """Remove reasoning tags and tool call markup from agent response.

    Args:
        text: Raw agent response text

    Returns:
        Cleaned response without thinking markers or tool markup
    """
    # Remove <think> ... </think> blocks
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # Remove tool call markup
    text = re.sub(r'<toolcalls.*?<toolcallend>', '', text, flags=re.DOTALL)
    text = re.sub(r'<toolcallsbegin>.*?<toolcallsend>', '', text, flags=re.DOTALL)
    text = re.sub(r'```json\s*\{.*?\}\s*```', '', text, flags=re.DOTALL)
    # Remove leading/trailing whitespace and extra blank lines
    text = text.strip()
    # Clean up excessive whitespace
    text = re.sub(r'\n\s*\n', '\n', text)
    return text


def search_assets(query: str, chat_history: list = None, temperature: float = 0.7, user_name: str = None, user_id: str = None, is_admin: bool = False) -> str:
    """Search for employee assets using the AI agent.

    Args:
        query: Natural language search query from the user
        chat_history: Optional conversation history for context
        temperature: Model temperature for response generation
        user_name: Optional current user's name for personalized search
        user_id: Optional current user's employee ID for access control
        is_admin: Whether current user is admin (bypasses access control)

    Returns:
        Agent response with search results (clean output without reasoning)
    """
    if chat_history is None:
        chat_history = []

    agent = create_asset_search_agent(temperature, user_name=user_name, user_id=user_id, is_admin=is_admin)

    response = agent.invoke({
        "messages": [{"role": "user", "content": query}],
    })

    # Extract the final AI message from the response
    # The last message should be an AIMessage with the final response
    if "messages" in response and response["messages"]:
        messages = response["messages"]

        # Find the last AIMessage (which is the final response after tool execution)
        ai_response = None
        for msg in reversed(messages):
            if hasattr(msg, "type") and msg.type == "ai":
                ai_response = msg
                break

        if ai_response and hasattr(ai_response, "content"):
            text = ai_response.content
            # Clean the response to remove reasoning tags
            return _clean_response(text)

    return "No results found."
