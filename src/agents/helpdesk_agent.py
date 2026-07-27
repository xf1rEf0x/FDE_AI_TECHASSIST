"""HelpDeskAgent: LangChain agent for ticket creation and management."""

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
from langgraph.prebuilt import create_react_agent
from src.tools.ticket_tools import (
    create_ticket_tool,
    check_ticket_status_tool,
    list_tickets_tool,
)


class HelpDeskAgent:
    """
    LangChain agent for Help Desk operations.

    Handles ticket creation, status checking, and ticket listing with user scoping.
    Uses tool calling to invoke the three ticket tools.
    """

    def __init__(self, user_email: str, model_name: str = "gemini-2.0-flash"):
        """
        Initialize HelpDeskAgent.

        Args:
            user_email: Email of the user (used for access control)
            model_name: Name of the Gemini model to use
        """
        self.user_email = user_email

        # Initialize Gemini model with temperature=0 for deterministic responses
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0,
        )

        # Define wrapped tools that automatically scope to user_email
        @tool
        def create_ticket(title: str, description: str) -> dict:
            """Create a new support ticket for the current user."""
            return create_ticket_tool(self.user_email, title, description)

        @tool
        def check_ticket_status(ticket_id: str) -> dict:
            """Check the status of a ticket owned by the current user."""
            return check_ticket_status_tool(self.user_email, ticket_id)

        @tool
        def list_tickets() -> dict:
            """List all tickets owned by the current user."""
            return list_tickets_tool(self.user_email)

        self.tools = [create_ticket, check_ticket_status, list_tickets]

        # System prompt with access control guard
        system_prompt = f"""You are a helpful IT Support Help Desk Agent. Your role is to:
1. Creating support tickets for IT issues
2. Checking the status of existing tickets
3. Listing all tickets for the user

IMPORTANT: You are assisting user with email: {user_email}
- Users can ONLY create tickets for themselves
- Users can ONLY check tickets they own
- All ticket operations are scoped to this user's email automatically

When a user asks to create a ticket:
- Use the create_ticket tool with title and description
- Confirm the ticket was created successfully

When a user asks to check a ticket status:
- Use the check_ticket_status tool with the ticket ID
- Display the ticket details including title, status, and description

When a user asks to list their tickets:
- Use the list_tickets tool
- Show a summary of all their tickets

Always be helpful and professional. Only refer to tickets that belong to this user."""

        # Create the ReAct agent using LangGraph
        self.executor = create_react_agent(
            self.llm,
            self.tools,
            prompt=system_prompt,
        )

    def run(self, user_input: str) -> str:
        """
        Run the agent with user input and return response text.

        Args:
            user_input: The user's message/request

        Returns:
            The agent's response as a string
        """
        result = self.executor.invoke({"messages": [("user", user_input)]})
        # Extract the last message from the response
        if result and "messages" in result:
            messages = result["messages"]
            if messages:
                last_msg = messages[-1]
                # last_msg is a tuple (role, content) or an AIMessage
                if isinstance(last_msg, tuple):
                    return last_msg[1]
                else:
                    return last_msg.content
        return ""
