"""Unified HelpDesk tab UI module with intelligent agent routing."""

import streamlit as st
from src.agents.helpdesk_agent import HelpDeskAgent
from src.agents.software_agent import SoftwareRequestAgent
from src.asset_agent import search_assets
from src.intent_router import IntentRouter
from src.auth import is_admin, get_current_user


def render_helpdesk_tab(user_email: str):
    """
    Render unified HelpDesk tab with intelligent agent routing.

    Routes user queries to HelpDesk, Software Request, or Asset Search agents
    based on automatic intent detection.

    Args:
        user_email: Email of the current user
    """
    st.subheader("🎫 Help Desk")
    st.markdown("Ask about creating tickets, requesting software, or checking your assets. I'll route you to the right service.")

    # Get current user for asset search
    current_user = get_current_user()
    user_is_admin = is_admin()
    user_id = current_user.get("employee_id") if current_user else None

    # Initialize agents and router on first visit
    if "helpdesk_agent" not in st.session_state:
        st.session_state.helpdesk_agent = HelpDeskAgent(user_email)

    if "software_agent" not in st.session_state:
        st.session_state.software_agent = SoftwareRequestAgent(user_email, is_admin=user_is_admin)

    if "intent_router" not in st.session_state:
        st.session_state.intent_router = IntentRouter()

    # Unified message history across all three services
    if "unified_helpdesk_messages" not in st.session_state:
        st.session_state.unified_helpdesk_messages = []

    # Display chat history
    for message in st.session_state.unified_helpdesk_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    user_input = st.chat_input("Ask about tickets, software requests, or your assets...")

    if user_input:
        # Add user message to history
        st.session_state.unified_helpdesk_messages.append({
            "role": "user",
            "content": user_input
        })

        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)

        # Get response
        try:
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                message_placeholder.markdown("🤔 *Processing...*")

                # Detect intent
                intent_result = st.session_state.intent_router.detect_intent(
                    user_input,
                    st.session_state.unified_helpdesk_messages[:-1]
                )

                response = ""

                # Route to appropriate agent
                if intent_result["clarification"]:
                    response = intent_result["clarification"]
                elif intent_result["intent"] == "helpdesk":
                    response = st.session_state.helpdesk_agent.run(user_input)
                elif intent_result["intent"] == "software_request":
                    response = st.session_state.software_agent.run(user_input)
                elif intent_result["intent"] == "asset_search":
                    response = search_assets(
                        user_input,
                        chat_history=st.session_state.unified_helpdesk_messages[:-1],
                        temperature=0.7,
                        user_name=current_user.get("name") if current_user else "User",
                        user_id=user_id,
                        is_admin=user_is_admin,
                        provider=st.session_state.get("provider", "gemini").lower()
                    )
                else:
                    response = "I'm not sure how to help with that. Could you clarify if you need: (1) a support ticket, (2) software installation, or (3) information about your assets?"

                message_placeholder.markdown(response)

            # Add assistant message to history
            st.session_state.unified_helpdesk_messages.append({
                "role": "assistant",
                "content": response
            })

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

    # Show admin tools if applicable
    if user_is_admin:
        with st.expander("🔑 Admin Tools"):
            st.info("You have admin permissions for software request approvals.")
            st.markdown("Use the Software Request feature to manage pending requests.")
