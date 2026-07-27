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
    import html
    escaped_content = html.escape(content)

    if role == "user":
        st.html(
            f"""
            <div style='display: flex; justify-content: flex-end; margin: 12px 0;'>
                <div style='background-color: {COLOR_USER_BG}; border-radius: 8px; padding: 12px 16px; max-width: 70%; text-align: left;'>
                    <div style='color: #1f2937; font-size: 0.95em;'>{escaped_content}</div>
                    {f"<div style='font-size: 0.8em; color: #6b7280; margin-top: 6px;'>{timestamp}</div>" if timestamp else ""}
                </div>
            </div>
            """
        )
    elif role == "assistant":
        st.html(
            f"""
            <div style='display: flex; justify-content: flex-start; margin: 12px 0;'>
                <div style='background-color: white; border-left: 4px solid {COLOR_PRIMARY}; border-radius: 4px; padding: 12px 16px; max-width: 70%;'>
                    <div style='color: #1f2937; font-size: 0.95em;'>{escaped_content}</div>
                    {f"<div style='font-size: 0.8em; color: #6b7280; margin-top: 6px;'>{timestamp}</div>" if timestamp else ""}
                </div>
            </div>
            """
        )
    else:
        st.html(
            f"""
            <div style='display: flex; justify-content: center; margin: 12px 0;'>
                <div style='background-color: {COLOR_SURFACE}; border-radius: 4px; padding: 12px 16px; max-width: 80%; text-align: center;'>
                    <div style='color: {COLOR_NEUTRAL}; font-size: 0.9em;'>{escaped_content}</div>
                    {f"<div style='font-size: 0.8em; color: #999999; margin-top: 6px;'>{timestamp}</div>" if timestamp else ""}
                </div>
            </div>
            """
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


