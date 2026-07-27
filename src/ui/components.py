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
    elif input_type in ("text", "password", "number"):
        value = st.text_input("", key=key, type=input_type, help=help_text or "", **kwargs)
    else:
        raise ValueError(f"Invalid input_type: {input_type}")

    return value
