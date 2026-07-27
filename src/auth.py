"""Authentication helpers for demo app."""

import streamlit as st
from src.auth_config import USERS


def login(email: str, password: str) -> dict | None:
    """
    Validate email/password against hardcoded users.
    Returns user dict if valid, None otherwise.
    """
    if email not in USERS:
        return None

    user = USERS[email]
    if user["password"] != password:
        return None

    # Store in session state
    st.session_state.user = {
        "email": email,
        "employee_id": user["employee_id"],
        "name": user["name"],
        "role": user["role"]
    }
    return st.session_state.user


def logout() -> None:
    """Clear login session."""
    if "user" in st.session_state:
        del st.session_state.user
    st.rerun()


def get_current_user() -> dict | None:
    """Get currently logged-in user or None."""
    return st.session_state.get("user")


def is_admin() -> bool:
    """Check if current user is admin."""
    user = get_current_user()
    return user is not None and user.get("role") == "admin"
