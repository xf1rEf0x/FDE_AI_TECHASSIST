"""Unified HelpDesk tab UI module with intelligent agent routing."""

import streamlit as st
from src.conversation import get_agent_instance
from src.auth import is_admin, get_current_user
from src.ui.components import header_card, action_card, message_container, info_box


def render_helpdesk_tab(user_email: str):
    """
    Render unified HelpDesk tab with intelligent agent routing.

    Routes user queries to HelpDesk, Software Request, or Asset Search agents
    based on automatic intent detection.

    Args:
        user_email: Email of the current user
    """
    # Header
    header_card("Help Desk", "Create tickets, request software, or check your assets")
    st.divider()

    # Get current user for asset search
    current_user = get_current_user()
    user_is_admin = is_admin()
    user_id = current_user.get("employee_id") if current_user else None

    # Initialize unified agent on first visit
    if "helpdesk_agent" not in st.session_state:
        st.session_state.helpdesk_agent = get_agent_instance(user_email, "employee", temperature=0.0)

    # Unified message history across all three services
    if "unified_helpdesk_messages" not in st.session_state:
        st.session_state.unified_helpdesk_messages = []

    # Show quick action cards if no conversation started
    if not st.session_state.unified_helpdesk_messages:
        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            if action_card("Create Ticket", "Report an issue", "📋", "helpdesk_create_ticket"):
                st.session_state.helpdesk_input_prefill = "I need to create a support ticket"
        with col2:
            if action_card("Request Software", "Install software", "💾", "helpdesk_request_software"):
                st.session_state.helpdesk_input_prefill = "I need to request software"
        with col3:
            if action_card("Check Assets", "View your devices", "🖥️", "helpdesk_check_assets"):
                st.session_state.helpdesk_input_prefill = "What assets do I have?"
        st.divider()

    # Chat history (scrolls naturally)
    for message in st.session_state.unified_helpdesk_messages:
        message_container(message["content"], message["role"])

    # Chat input (pinned at bottom via native layout)
    user_input = st.chat_input("Ask about tickets, software requests, or your assets...")
    if st.session_state.get("helpdesk_input_prefill"):
        del st.session_state.helpdesk_input_prefill

    if user_input:
        # Add user message to history
        st.session_state.unified_helpdesk_messages.append({
            "role": "user",
            "content": user_input
        })
        st.rerun()

    # Get response after messages are shown
    if len(st.session_state.unified_helpdesk_messages) > 0 and st.session_state.unified_helpdesk_messages[-1]["role"] == "user":
        # Show thinking placeholder in chat
        message_container("🤔 Thinking...", "assistant")

        try:
            # Use unified agent for all request types (ticket, software, asset)
            response = st.session_state.helpdesk_agent.invoke(
                st.session_state.unified_helpdesk_messages[-1]["content"]
            )

            # Add assistant message to history
            st.session_state.unified_helpdesk_messages.append({
                "role": "assistant",
                "content": response
            })
            st.rerun()

        except Exception as e:
            info_box(f"Error: {str(e)}", "error")

    # Show admin tools if applicable
    if user_is_admin:
        with st.expander("🔑 Admin Tools"):
            info_box("You have admin permissions for software request approvals.", "info")
            st.markdown("Use the Software Request feature to manage pending requests.")
