"""TechAssist AI Phase 1: Streamlit chatbot with role-based personas."""

import warnings
warnings.filterwarnings("ignore", module="transformers.*")

import os
import streamlit as st
from src.conversation import get_response, get_response_stream
from src.prompts import get_available_roles, get_system_prompt, get_prompt_templates
from src.utils import format_message
from src.sessions import (
    create_session,
    get_session,
    delete_session,
    list_sessions,
    update_session,
)
from src.ui.helpdesk_tab import render_helpdesk_tab
from src.ui.external_services_tab import render_external_services_tab
from src.ui.components import form_group, info_box, status_badge, sidebar_section
from src.auth import login, logout, get_current_user, is_admin

# ============================================================================
# LOGIN GATE
# ============================================================================

st.set_page_config(
    page_title="TechAssist AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Track login attempts
if "login_attempted" not in st.session_state:
    st.session_state.login_attempted = False

# Check if user is logged in
if not get_current_user():
    # Center the login card using columns
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        # Logo and tagline
        st.markdown("# 🤖 TechAssist AI")
        st.markdown("*IT Support, Simplified*")
        st.divider()

        # Login form
        with st.form("login_form"):
            email = form_group(
                "Email",
                "text",
                help_text="e.g., alice@techassist.com",
                placeholder="Enter your email"
            )
            password = form_group(
                "Password",
                "password",
                help_text="Enter your password"
            )
            submitted = st.form_submit_button("Login", use_container_width=True)

            if submitted:
                st.session_state.login_attempted = True
                if not email or not password:
                    info_box("Please enter email and password.", "error")
                else:
                    user = login(email, password)
                    if user:
                        info_box(f"Welcome, {user['name']}!", "success")
                        st.rerun()
                    else:
                        info_box("Invalid email or password.", "error")

        # Demo credentials hint - only show on first load
        if not st.session_state.login_attempted:
            info_box("""**Demo credentials:**
- alice@techassist.com / password123
- bob@techassist.com / password123
- carol@techassist.com / password123
- david@techassist.com / password123
- engineer@techassist.com / engineer123
- admin@techassist.com / admin123""", "info")
    st.stop()

# ============================================================================
# MAIN APP (user is logged in)
# ============================================================================

st.title("🤖 TechAssist AI Support Assistant")
st.markdown("*Your friendly IT support assistant for TechAssist Solutions*")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Role is now bound to logged-in user's role, not settable
current_user = get_current_user()
if current_user:
    st.session_state.role = current_user.get("role", "employee")

if "template_selected" not in st.session_state:
    st.session_state.template_selected = None

if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None

if "temperature" not in st.session_state:
    st.session_state.temperature = 0.7

if "provider" not in st.session_state:
    st.session_state.provider = "huggingface"

# Sidebar: Role and model selector
with st.sidebar:
    st.header("Settings")

    # Current user info and logout
    current_user = get_current_user()
    if current_user:
        st.markdown(f"**Logged in as:** {current_user['name']}")
        st.markdown(status_badge(current_user['role'].capitalize(), "completed"))
        if st.button("🚪 Logout", use_container_width=True):
            logout()

    # Settings section with provider and temperature controls
    def render_settings():
        st.session_state.provider = st.selectbox(
            "LLM Provider:",
            ["HuggingFace", "Gemini"],
            index=0 if st.session_state.provider.lower() == "huggingface" else 1,
            help="Switch between HuggingFace (DeepSeek-R1) and Gemini (Google)"
        )

        # Dynamic info box
        if st.session_state.provider.lower() == "huggingface":
            info_box("Using HuggingFace model: DeepSeek-R1", "info")
        else:
            info_box("Using Gemini model: gemini-pro", "info")

        # Temperature slider
        st.session_state.temperature = st.slider(
            "Temperature:",
            min_value=0.0,
            max_value=2.0,
            value=st.session_state.temperature,
            step=0.1,
            help="Lower = more focused/deterministic, Higher = more creative/random"
        )

    sidebar_section("⚙️ Settings", render_settings)

    # Show current role info
    with st.expander("ℹ️ About your role"):
        st.markdown(get_system_prompt(st.session_state.role))

    # Session history section
    def render_session_history():
        sessions = list_sessions()
        if sessions:
            for session_id, session_data in sessions:
                col1, col2 = st.columns([3, 1])
                with col1:
                    if st.button(
                        f"🔄 {session_data['name'][:40]}",
                        use_container_width=True,
                        key=f"load_{session_id}"
                    ):
                        loaded = get_session(session_id)
                        if loaded:
                            st.session_state.messages = loaded["messages"]
                            st.session_state.role = loaded["role"]
                            st.session_state.current_session_id = session_id
                            st.success(f"✓ Loaded: {loaded['name']}")
                            st.rerun()
                with col2:
                    if st.button("🗑️", key=f"delete_{session_id}", help="Delete session"):
                        delete_session(session_id)
                        if st.session_state.current_session_id == session_id:
                            st.session_state.current_session_id = None
                            st.session_state.messages = []
                        st.success("Deleted")
                        st.rerun()
            st.caption(f"Total: {len(sessions)} session(s)")
        else:
            st.caption("💬 Start a conversation to create a session")

    sidebar_section("📋 Session History", render_session_history)

    # Clear conversation button
    if st.button("New Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.template_selected = None
        st.session_state.current_session_id = None
        st.success("Conversation cleared!")
        st.rerun()

# Main content tabs
tabs_list = ["💬 AI Chat", "🎫 HelpDesk"]
if current_user.get("role") == "engineer":
    tabs_list.append("☁️ External Services Status")

tab_objects = st.tabs(tabs_list)
tab_chat = tab_objects[0]
tab_helpdesk = tab_objects[1]
tab_services = tab_objects[2] if len(tab_objects) > 2 else None

with tab_chat:
    st.subheader("Conversation")

    # Chat history container (scrollable)
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Prompt templates (shown only when empty)
    if not st.session_state.messages:
        st.markdown("**Quick questions for your role:**")
        templates = get_prompt_templates(st.session_state.role)
        cols = st.columns(len(templates))
        for idx, template in enumerate(templates):
            with cols[idx]:
                if st.button(template, use_container_width=True, key=f"template_{idx}_{template[:10]}"):
                    st.session_state.template_selected = template
                    st.rerun()

    # User input (pinned at bottom via native layout)
    user_input = st.chat_input("Ask me anything about IT support...")

    # Handle template selection
    if st.session_state.template_selected and not st.session_state.messages:
        user_input = st.session_state.template_selected
        st.session_state.template_selected = None

    if user_input:
        # Validate input
        if not user_input.strip():
            st.warning("Please enter a message.")
            st.stop()

        # Add user message to history
        user_message = format_message("user", user_input)
        st.session_state.messages.append(user_message)
        st.rerun()

    # Get and display assistant response after messages are shown
    if len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "user":
        try:
            full_response = ""
            with st.spinner("🤔 Thinking..."):
                # Collect full response with streaming
                for chunk in get_response_stream(st.session_state.messages[-1]["content"], st.session_state.role, st.session_state.messages[:-1], temperature=st.session_state.temperature, provider=st.session_state.provider.lower()):
                    full_response += chunk

            # Add assistant message to history
            assistant_message = format_message("assistant", full_response)
            st.session_state.messages.append(assistant_message)

            # Auto-create session on first response if not already in a session
            if not st.session_state.current_session_id:
                st.session_state.current_session_id = create_session(st.session_state.role, st.session_state.messages)

            # Auto-save current session
            if st.session_state.current_session_id:
                update_session(st.session_state.current_session_id, st.session_state.messages)

            st.rerun()

        except ValueError as e:
            st.error(f"❌ {e}")
        except Exception as e:
            error_msg = str(e)
            st.error(f"❌ Error: {error_msg}")
            if "API" in error_msg or "key" in error_msg.lower():
                st.info("Please check your HuggingFace API key in `.env` and try again.")

with tab_helpdesk:
    render_helpdesk_tab(current_user.get("email"))

if tab_services is not None:
    with tab_services:
        render_external_services_tab()
