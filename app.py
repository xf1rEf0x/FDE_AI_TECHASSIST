"""TechAssist AI Phase 1: Streamlit chatbot with role-based personas."""

import os
import streamlit as st
from src.conversation import get_response, get_response_stream
from src.prompts import get_available_roles, get_system_prompt, get_prompt_templates
from src.config import get_gemini_model, get_available_models
from src.utils import format_message

st.set_page_config(
    page_title="TechAssist AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🤖 TechAssist AI Support Assistant")
st.markdown("*Your friendly IT support assistant for TechAssist Solutions*")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "role" not in st.session_state:
    st.session_state.role = "employee"

if "model" not in st.session_state:
    st.session_state.model = get_gemini_model()

if "template_selected" not in st.session_state:
    st.session_state.template_selected = None

# Sidebar: Role and model selector
with st.sidebar:
    st.header("Settings")

    available_roles = get_available_roles()
    selected_role = st.selectbox(
        "Select your role:",
        available_roles,
        index=available_roles.index(st.session_state.role),
        help="Choose your role to get personalized IT support"
    )

    # Update role and clear history if changed
    if selected_role != st.session_state.role:
        st.session_state.role = selected_role
        st.session_state.messages = []
        st.info(f"✓ Switched to {selected_role} role. Chat history cleared.")

    # Model selector
    available_models = get_available_models()
    selected_model = st.selectbox(
        "Select AI model:",
        available_models,
        index=available_models.index(st.session_state.model),
        help="Choose the Gemini model to use for responses"
    )

    # Update model if changed
    if selected_model != st.session_state.model:
        st.session_state.model = selected_model
        os.environ["GEMINI_MODEL"] = selected_model
        st.success(f"✓ Switched to {selected_model}")

    # Show current role info
    with st.expander("ℹ️ About your role"):
        st.markdown(get_system_prompt(st.session_state.role))

    # Clear conversation button
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.template_selected = None
        st.success("Conversation cleared!")
        st.rerun()

# Display conversation history
st.subheader("Conversation")
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
user_input = st.chat_input("Ask me anything about IT support...")

# Prompt templates below chat input
if not st.session_state.messages:
    st.markdown("**Quick questions for your role:**")
    templates = get_prompt_templates(st.session_state.role)
    cols = st.columns(len(templates))
    for idx, template in enumerate(templates):
        with cols[idx]:
            if st.button(template, use_container_width=True, key=f"template_{idx}_{template[:10]}"):
                st.session_state.template_selected = template
                st.rerun()

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

    # Display user message
    with st.chat_message("user"):
        st.markdown(user_input)

    # Get and display assistant response
    try:
        with st.chat_message("assistant"):
            message_placeholder = st.empty()

            # Show thinking animation
            message_placeholder.markdown("🤔 *Thinking...*")

            full_response = ""

            # Use streaming to display response in real-time
            for chunk in get_response_stream(user_input, st.session_state.role, st.session_state.messages[:-1], st.session_state.model):
                full_response += chunk
                message_placeholder.markdown(full_response + "▌")

            # Final response without cursor
            message_placeholder.markdown(full_response)

        # Add assistant message to history
        assistant_message = format_message("assistant", full_response)
        st.session_state.messages.append(assistant_message)

    except ValueError as e:
        st.error(f"❌ {e}")
    except Exception as e:
        error_msg = str(e)
        st.error(f"❌ Error: {error_msg}")
        if "API" in error_msg or "key" in error_msg.lower():
            st.info("Please check your Google API key in `.env` and try again.")
