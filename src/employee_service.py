"""Employee Service module for AI-powered IT support actions."""

import streamlit as st
from src.asset_agent import search_assets
from src.auth import get_current_user, is_admin


# ============================================================================
# EMPLOYEE ASSETS
# ============================================================================

def render_employee_assets():
    """Render Employee Assets service tab with AI Agent-powered search."""
    st.subheader("🏢 Employee Assets")

    # Get current user info
    current_user = get_current_user()
    if not current_user:
        st.warning("Please login to view assets.")
        return

    user_id = current_user.get("employee_id")
    user_admin = is_admin()

    st.markdown("Search for your assigned assets using natural language. Ask about laptops, monitors, software licenses, printers, or anything else.")

    # Initialize chat history for this session
    if "asset_chat_history" not in st.session_state:
        st.session_state.asset_chat_history = []

    if "asset_search_temperature" not in st.session_state:
        st.session_state.asset_search_temperature = 0.7

    # Display chat history
    st.markdown("### Asset Search Conversation")
    for message in st.session_state.asset_chat_history:
        role = message["role"]
        content = message["content"]
        with st.chat_message(role):
            st.markdown(content)

    # User input
    user_query = st.chat_input("Ask about your assets (e.g., 'Show me my laptop', 'Find my Microsoft Office license')...")

    if user_query:
        # Add user message to history
        st.session_state.asset_chat_history.append({
            "role": "user",
            "content": user_query
        })

        # Display user message
        with st.chat_message("user"):
            st.markdown(user_query)

        # Get agent response
        try:
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                message_placeholder.markdown("🤔 *Searching assets...*")

                # Call asset search agent with user_id and admin flag
                response = search_assets(
                    user_query,
                    chat_history=st.session_state.asset_chat_history[:-1],
                    temperature=st.session_state.asset_search_temperature,
                    user_name=current_user.get("name"),
                    user_id=user_id,  # NEW
                    is_admin=user_admin,  # NEW
                    provider=st.session_state.provider.lower()  # Pass selected provider
                )

                message_placeholder.markdown(response)

            # Add assistant message to history
            st.session_state.asset_chat_history.append({
                "role": "assistant",
                "content": response
            })

        except Exception as e:
            st.error(f"❌ Error searching assets: {str(e)}")

    # Optional: User identification (for "me" queries)
    with st.expander("👤 Your Info"):
        st.markdown(f"**Name:** {current_user.get('name')}")
        st.markdown(f"**Employee ID:** {user_id}")
        st.markdown(f"**Role:** {current_user.get('role').capitalize()}")

    # Sidebar controls
    with st.sidebar:
        if st.button("Clear Asset Search History"):
            st.session_state.asset_chat_history = []
            st.success("Asset search history cleared!")
            st.rerun()


# ============================================================================
# HELPDESK
# ============================================================================

def render_helpdesk():
    """Render HelpDesk service tab with sub-actions."""
    st.subheader("🎫 HelpDesk")
    st.markdown("Manage your support tickets")

    action = st.radio(
        "Select action:",
        ["Create Ticket", "Check Status"],
        horizontal=True,
    )

    if action == "Create Ticket":
        _render_create_ticket()
    elif action == "Check Status":
        _render_check_ticket_status()


def _render_create_ticket():
    """Template for Create HelpDesk Ticket action."""
    st.write("Create a new support ticket for your IT issue.")

    with st.form("create_ticket_form"):
        issue_type = st.selectbox(
            "Issue Type:",
            [
                "Hardware",
                "Software",
                "Network/VPN",
                "Access/Permissions",
                "Other",
            ],
        )
        title = st.text_input("Issue Title:", placeholder="Brief description of your issue")
        description = st.text_area(
            "Detailed Description:",
            placeholder="Provide more details about your issue",
        )
        priority = st.selectbox("Priority:", ["Low", "Medium", "High", "Critical"])

        submitted = st.form_submit_button("🎫 Create Ticket", use_container_width=True)
        if submitted:
            if title.strip() and description.strip():
                st.success("✓ Support ticket created successfully!")
                st.info("Your ticket ID: TK-2024-001234")
            else:
                st.warning("Please fill in title and description.")


def _render_check_ticket_status():
    """Template for Check Ticket Status action."""
    st.write("Check the status of your existing support tickets.")

    with st.form("check_ticket_form"):
        ticket_id = st.text_input(
            "Ticket ID:",
            placeholder="e.g., TK-2024-001234",
        )

        submitted = st.form_submit_button("📊 Check Status", use_container_width=True)
        if submitted:
            if ticket_id.strip():
                st.info("🔄 Checking ticket status... (implementation pending)")
            else:
                st.warning("Please enter a ticket ID.")


# ============================================================================
# SOFTWARE REQUEST
# ============================================================================

def render_software_request():
    """Render Software Request service tab."""
    st.subheader("💾 Software Request")
    st.markdown("Request software installation or licenses")

    with st.form("software_request_form"):
        software_name = st.text_input(
            "Software Name:",
            placeholder="e.g., Microsoft Project, Adobe Creative Suite",
        )
        justification = st.text_area(
            "Business Justification:",
            placeholder="Why do you need this software?",
        )
        urgency = st.selectbox("Urgency:", ["Low", "Medium", "High"])

        submitted = st.form_submit_button("💾 Request Software", use_container_width=True)
        if submitted:
            if software_name.strip() and justification.strip():
                st.success("✓ Software request submitted for approval.")
            else:
                st.warning("Please fill in software name and justification.")


# ============================================================================
# USER ACCOUNT
# ============================================================================

def render_user_account():
    """Render User Account service tab with sub-actions."""
    st.subheader("👤 User Account")
    st.markdown("Manage your account access and security")

    action = st.radio(
        "Select action:",
        ["Reset Password", "Unlock Account"],
        horizontal=True,
    )

    if action == "Reset Password":
        _render_reset_password_request()
    elif action == "Unlock Account":
        _render_unlock_user_account()


def _render_reset_password_request():
    """Template for Reset Password Request action."""
    st.write("Request a password reset for your account.")

    with st.form("reset_password_form"):
        account_type = st.selectbox(
            "Account Type:",
            ["Windows/Active Directory", "Email", "VPN", "Other"],
        )
        reason = st.text_area(
            "Reason for reset (optional):",
            placeholder="e.g., Forgot password, account locked",
        )

        submitted = st.form_submit_button("🔐 Request Reset", use_container_width=True)
        if submitted:
            st.success(
                "✓ Password reset request submitted. Check your email for further instructions."
            )


def _render_unlock_user_account():
    """Template for Unlock User Account action."""
    st.write("Request to unlock your locked account.")

    with st.form("unlock_account_form"):
        account_type = st.selectbox(
            "Account Type:",
            ["Windows/Active Directory", "Email", "VPN", "Other"],
        )
        reason = st.text_area(
            "What happened? (optional):",
            placeholder="e.g., Too many failed login attempts",
        )

        submitted = st.form_submit_button("🔓 Request Unlock", use_container_width=True)
        if submitted:
            st.success(
                "✓ Account unlock request submitted. Your account will be unlocked shortly."
            )
