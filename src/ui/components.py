"""
UI Component Library Base and Color System for TechAssist AI.

This module provides a centralized system for color constants, spacing units,
and component building blocks to ensure consistency across the application.
"""

import streamlit as st
from typing import Optional, Tuple, Any

# Color Constants
COLOR_PRIMARY = "#0066cc"
COLOR_SUCCESS = "#10b981"
COLOR_WARNING = "#f59e0b"
COLOR_ERROR = "#ef4444"
COLOR_NEUTRAL = "#6b7280"
COLOR_SURFACE = "#f9fafb"
COLOR_USER_BG = "#dbeafe"

# Spacing Constants (in pixels)
SPACING_UNIT = 12
SPACING_SM = SPACING_UNIT * 1  # 12px
SPACING_MD = SPACING_UNIT * 2  # 24px
SPACING_LG = SPACING_UNIT * 3  # 36px
SPACING_XL = SPACING_UNIT * 4  # 48px


def header_card(title: str, description: Optional[str] = None, action_button: Optional[Tuple[str, str, str]] = None) -> None:
    """
    Render a section header with optional description and action button.

    Args:
        title: Bold section heading text
        description: Optional italic secondary text
        action_button: Optional tuple of (button_text, button_key, button_help)
    """
    col1, col2 = st.columns([1, 0.25]) if action_button else (st.columns([1])[0], None)

    with col1:
        st.markdown(f"### {title}")
        if description:
            st.markdown(f"*{description}*")

    if col2 and action_button:
        with col2:
            button_text, button_key, button_help = action_button
            st.button(button_text, key=button_key, help=button_help)


def status_badge(label: str, status: str) -> str:
    """
    Return a colored status badge with emoji indicator.

    Args:
        label: The label text to display
        status: One of "operational", "degraded", "down", "pending", "completed"

    Returns:
        Formatted badge string with emoji prefix
    """
    emoji_map = {
        "operational": "✅",
        "degraded": "⚠️",
        "down": "❌",
        "pending": "⏳",
        "completed": "✓",
    }
    emoji = emoji_map.get(status, "")
    if emoji:
        return f"{emoji} {label}"
    return label


def form_group(label: str, input_type: str, help_text: Optional[str] = None, key: Optional[str] = None, **kwargs) -> Any:
    """
    Wrap an input field with label and help text, consistent spacing.

    Args:
        label: Bold label text
        input_type: One of "text", "password", "textarea", "number"
        help_text: Optional caption text below the input
        key: Optional Streamlit widget key
        **kwargs: Additional arguments to pass to the input widget

    Returns:
        The input value from the widget
    """
    st.markdown(f"**{label}**")

    if input_type == "textarea":
        value = st.text_area("", key=key, help=help_text or "", **kwargs)
    elif input_type == "text":
        value = st.text_input("", key=key, help=help_text or "", **kwargs)
    elif input_type == "password":
        value = st.text_input("", key=key, type="password", help=help_text or "", **kwargs)
    elif input_type == "number":
        value = st.number_input("", key=key, help=help_text or "", **kwargs)
    else:
        raise ValueError(f"Invalid input_type: {input_type}")

    return value


def metric_tile(title: str, value: str, icon: str = "", subtitle: Optional[str] = None) -> None:
    """
    Display a key metric (stat tile) with optional icon and subtitle.

    Args:
        title: Metric name
        value: Metric value (string, e.g., "12")
        icon: Optional emoji icon
        subtitle: Optional additional text below value
    """
    cols = st.columns([1])
    with cols[0]:
        # Display icon if provided, followed by large value
        if icon:
            st.markdown(f"<div style='text-align: center;'><span style='font-size: 2em;'>{icon}</span></div>", unsafe_allow_html=True)

        st.markdown(f"<div style='text-align: center; font-size: 2.5em; font-weight: bold; color: {COLOR_PRIMARY};'>{value}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='text-align: center; font-size: 1em; color: {COLOR_NEUTRAL};'>{title}</div>", unsafe_allow_html=True)

        if subtitle:
            st.markdown(f"<div style='text-align: center; font-size: 0.9em; color: {COLOR_NEUTRAL}; margin-top: 6px;'>{subtitle}</div>", unsafe_allow_html=True)


def action_card(title: str, description: str, icon: str, key: str) -> bool:
    """
    Render a clickable card for primary user actions.

    Args:
        title: Card title
        description: Card description
        icon: Emoji icon
        key: Unique Streamlit key for button

    Returns:
        True if clicked, False otherwise
    """
    # Use a button with full width and custom formatting via markdown
    button_text = f"{icon} {title}\n_{description}_"
    return st.button(button_text, key=key, use_container_width=True)


def message_container(content: str, role: str, timestamp: Optional[str] = None) -> None:
    """
    Render a single chat message with styling based on role.

    Args:
        content: Message text (markdown)
        role: One of "user", "assistant", "system"
        timestamp: Optional timestamp string
    """
    if role == "user":
        # User messages: right-aligned with light blue background
        st.markdown(
            f"""
            <div style='display: flex; justify-content: flex-end; margin: 12px 0;'>
                <div style='background-color: {COLOR_USER_BG}; border-radius: 8px; padding: 12px 16px; max-width: 70%; text-align: left;'>
                    <div style='color: #1f2937; font-size: 0.95em;'>{content}</div>
                    {f"<div style='font-size: 0.8em; color: #6b7280; margin-top: 6px;'>{timestamp}</div>" if timestamp else ""}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    elif role == "assistant":
        # Assistant messages: left-aligned with neutral background and primary border
        st.markdown(
            f"""
            <div style='display: flex; justify-content: flex-start; margin: 12px 0;'>
                <div style='background-color: white; border-left: 4px solid {COLOR_PRIMARY}; border-radius: 4px; padding: 12px 16px; max-width: 70%;'>
                    <div style='color: #1f2937; font-size: 0.95em;'>{content}</div>
                    {f"<div style='font-size: 0.8em; color: #6b7280; margin-top: 6px;'>{timestamp}</div>" if timestamp else ""}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:  # system
        # System messages: centered with neutral styling
        st.markdown(
            f"""
            <div style='display: flex; justify-content: center; margin: 12px 0;'>
                <div style='background-color: {COLOR_SURFACE}; border-radius: 4px; padding: 12px 16px; max-width: 80%; text-align: center;'>
                    <div style='color: {COLOR_NEUTRAL}; font-size: 0.9em;'>{content}</div>
                    {f"<div style='font-size: 0.8em; color: #999999; margin-top: 6px;'>{timestamp}</div>" if timestamp else ""}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )


def info_box(message: str, severity: str, dismissible: bool = False) -> None:
    """
    Display a color-coded alert box with severity indicator and optional dismiss button.

    Uses native Streamlit alert functions (st.info, st.success, st.warning, st.error)
    with emoji prefixes for visual clarity.

    Args:
        message: Alert message text
        severity: One of "info", "success", "warning", "error"
        dismissible: If True, note that dismissal is not natively supported in Streamlit
                    (component is for documentation purposes; actual dismissal would require
                    st.session_state management at the caller level)

    Returns:
        None (renders via Streamlit)
    """
    emoji_map = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌",
    }
    emoji = emoji_map.get(severity, "")
    display_message = f"{emoji} {message}" if emoji else message

    if severity == "info":
        st.info(display_message)
    elif severity == "success":
        st.success(display_message)
    elif severity == "warning":
        st.warning(display_message)
    elif severity == "error":
        st.error(display_message)
    else:
        st.info(display_message)


def sidebar_section(title: str, content_func: callable, expanded: bool = True) -> None:
    """
    Render a consistently-styled sidebar section with title and divider.

    Parameters:
        title: Section title to display in the sidebar
        content_func: Callable that renders the section's content.
                     Will be called within the sidebar context.
        expanded: If True, section header is displayed; Streamlit does not have
                 native collapsible sidebar sections, so this is informational.

    Returns:
        None (renders via Streamlit sidebar)
    """
    with st.sidebar:
        st.markdown(f"**{title}**")
        content_func()
        st.divider()


def demo_components():
    """
    Demo all components for manual testing.
    Run: streamlit run src/ui/components.py
    """
    st.title("🎨 TechAssist UI Component Demo")

    # Demo header_card
    st.subheader("header_card")
    header_card("Section Title", "Optional description text")

    # Demo status_badge
    st.subheader("status_badge")
    for status in ["operational", "degraded", "down", "pending", "completed"]:
        st.write(status_badge(f"Service {status.title()}", status))

    # Demo metric_tile
    st.subheader("metric_tile")
    col1, col2, col3 = st.columns(3)
    with col1:
        metric_tile("Active Sessions", "12", "💬")
    with col2:
        metric_tile("Pending Tickets", "5", "🎫")
    with col3:
        metric_tile("Admin Users", "3", "👤")

    # Demo action_card
    st.subheader("action_card")
    col1, col2, col3 = st.columns(3)
    with col1:
        action_card("Create Ticket", "Report an issue", "📋", "demo_action_1")
    with col2:
        action_card("Request Software", "Install software", "💾", "demo_action_2")
    with col3:
        action_card("Check Assets", "View your devices", "🖥️", "demo_action_3")

    # Demo message_container
    st.subheader("message_container")
    message_container("Hi, can you help me reset my password?", "user")
    message_container("Of course! I can help you reset your password. Let me gather some information first.", "assistant")

    # Demo form_group
    st.subheader("form_group")
    form_group("Username", "text", help_text="Enter your username", key="demo_username")
    form_group("Password", "password", help_text="Enter your password", key="demo_password")

    # Demo info_box
    st.subheader("info_box")
    col1, col2 = st.columns(2)
    with col1:
        info_box("This is an info message", "info")
        info_box("This is a success message", "success")
    with col2:
        info_box("This is a warning message", "warning")
        info_box("This is an error message", "error")


if __name__ == "__main__":
    st.set_page_config(page_title="Component Demo", layout="wide")
    demo_components()
