"""Help Desk tab UI module with agent-powered chat interface."""

import streamlit as st
from src.agents.helpdesk_agent import HelpDeskAgent


def render_helpdesk_tab(user_email: str):
    """
    Render the Help Desk tab with ticket creation and status checking.

    Uses HelpDeskAgent with a chat interface for natural language ticket operations.

    Args:
        user_email: Email of the current user (for agent scoping)
    """
    st.subheader("🎫 Help Desk")
    st.markdown("Create tickets, check status, and manage your support requests.")

    # Initialize agent on first visit
    if "helpdesk_agent" not in st.session_state:
        st.session_state.helpdesk_agent = HelpDeskAgent(user_email)

    # Initialize message history
    if "helpdesk_messages" not in st.session_state:
        st.session_state.helpdesk_messages = []

    # Display chat history
    for message in st.session_state.helpdesk_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    user_input = st.chat_input("Ask about creating or checking a ticket...")

    if user_input:
        # Add user message to history
        st.session_state.helpdesk_messages.append({
            "role": "user",
            "content": user_input
        })

        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)

        # Get agent response
        try:
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                message_placeholder.markdown("🤔 *Processing...*")

                # Run agent
                response = st.session_state.helpdesk_agent.run(user_input)

                message_placeholder.markdown(response)

            # Add assistant message to history
            st.session_state.helpdesk_messages.append({
                "role": "assistant",
                "content": response
            })

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
