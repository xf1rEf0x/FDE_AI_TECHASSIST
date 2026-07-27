"""
Unit tests for UI component library base and color system.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.ui.components import (
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_ERROR,
    COLOR_NEUTRAL,
    COLOR_SURFACE,
    COLOR_USER_BG,
    SPACING_UNIT,
    SPACING_SM,
    SPACING_MD,
    SPACING_LG,
    SPACING_XL,
    header_card,
    status_badge,
    form_group,
    metric_tile,
    action_card,
    message_container,
)


def test_color_constants():
    """Verify all color constants are present and have correct hex values."""
    assert COLOR_PRIMARY == "#0066cc"
    assert COLOR_SUCCESS == "#10b981"
    assert COLOR_WARNING == "#f59e0b"
    assert COLOR_ERROR == "#ef4444"
    assert COLOR_NEUTRAL == "#6b7280"
    assert COLOR_SURFACE == "#f9fafb"
    assert COLOR_USER_BG == "#dbeafe"

    # Verify all colors are valid hex strings
    for color_name, color_value in [
        ("COLOR_PRIMARY", COLOR_PRIMARY),
        ("COLOR_SUCCESS", COLOR_SUCCESS),
        ("COLOR_WARNING", COLOR_WARNING),
        ("COLOR_ERROR", COLOR_ERROR),
        ("COLOR_NEUTRAL", COLOR_NEUTRAL),
        ("COLOR_SURFACE", COLOR_SURFACE),
        ("COLOR_USER_BG", COLOR_USER_BG),
    ]:
        assert isinstance(color_value, str), f"{color_name} should be a string"
        assert color_value.startswith("#"), f"{color_name} should start with #"
        assert len(color_value) == 7, f"{color_name} should be a valid hex color (7 chars)"


def test_spacing_constants():
    """Verify spacing constants are present and have correct values."""
    assert SPACING_UNIT == 12
    assert SPACING_SM == 12
    assert SPACING_MD == 24
    assert SPACING_LG == 36
    assert SPACING_XL == 48

    # Verify spacing values are integers
    for spacing_name, spacing_value in [
        ("SPACING_UNIT", SPACING_UNIT),
        ("SPACING_SM", SPACING_SM),
        ("SPACING_MD", SPACING_MD),
        ("SPACING_LG", SPACING_LG),
        ("SPACING_XL", SPACING_XL),
    ]:
        assert isinstance(spacing_value, int), f"{spacing_name} should be an integer"

    # Verify spacing multiples are correct
    assert SPACING_SM == SPACING_UNIT * 1
    assert SPACING_MD == SPACING_UNIT * 2
    assert SPACING_LG == SPACING_UNIT * 3
    assert SPACING_XL == SPACING_UNIT * 4


def test_status_badge():
    """Test badge formatting for all statuses."""
    assert status_badge("Operational", "operational") == "✅ Operational"
    assert status_badge("Degraded", "degraded") == "⚠️ Degraded"
    assert status_badge("Down", "down") == "❌ Down"
    assert status_badge("Pending", "pending") == "⏳ Pending"
    assert status_badge("Completed", "completed") == "✓ Completed"


def test_status_badge_unknown():
    """Test unknown status returns label unchanged."""
    assert status_badge("Unknown", "unknown") == "Unknown"
    assert status_badge("Custom", "invalid_status") == "Custom"


def test_form_group_signature():
    """Test function has correct parameters."""
    import inspect
    sig = inspect.signature(form_group)
    params = list(sig.parameters.keys())
    assert "label" in params
    assert "input_type" in params
    assert "help_text" in params
    assert "key" in params
    # Verify kwargs is supported
    assert any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())


def test_metric_tile_signature():
    """Test metric_tile has correct signature."""
    import inspect
    sig = inspect.signature(metric_tile)
    params = list(sig.parameters.keys())
    assert "title" in params
    assert "value" in params
    assert "icon" in params
    assert "subtitle" in params
    # Verify return type is None
    assert sig.return_annotation is None or sig.return_annotation == type(None)


def test_metric_tile_defaults():
    """Test metric_tile parameter defaults."""
    import inspect
    sig = inspect.signature(metric_tile)
    assert sig.parameters["icon"].default == ""
    assert sig.parameters["subtitle"].default is None


@patch("streamlit.columns")
@patch("streamlit.markdown")
def test_metric_tile_renders(mock_markdown, mock_columns):
    """Test metric_tile calls rendering functions."""
    # Mock the column context manager
    mock_col = MagicMock()
    mock_columns.return_value = [mock_col]
    mock_col.__enter__ = MagicMock(return_value=mock_col)
    mock_col.__exit__ = MagicMock(return_value=False)

    metric_tile("Test Metric", "42", "📊", "Additional info")

    # Verify streamlit functions were called
    mock_columns.assert_called_once()
    assert mock_markdown.call_count >= 3  # At least title, value, subtitle


def test_action_card_signature():
    """Test action_card has correct signature."""
    import inspect
    sig = inspect.signature(action_card)
    params = list(sig.parameters.keys())
    assert "title" in params
    assert "description" in params
    assert "icon" in params
    assert "key" in params
    # Verify return type is bool
    assert sig.return_annotation == bool


@patch("streamlit.button")
def test_action_card_returns_bool(mock_button):
    """Test action_card returns boolean."""
    mock_button.return_value = True
    result = action_card("Action", "Do something", "⚡", "action_key")
    assert isinstance(result, bool)
    assert result is True
    mock_button.assert_called_once()


def test_message_container_signature():
    """Test message_container has correct signature."""
    import inspect
    sig = inspect.signature(message_container)
    params = list(sig.parameters.keys())
    assert "content" in params
    assert "role" in params
    assert "timestamp" in params
    # Verify return type is None
    assert sig.return_annotation is None or sig.return_annotation == type(None)


def test_message_container_timestamp_default():
    """Test message_container timestamp parameter default."""
    import inspect
    sig = inspect.signature(message_container)
    assert sig.parameters["timestamp"].default is None


@patch("streamlit.markdown")
def test_message_container_user_message(mock_markdown):
    """Test message_container renders user messages correctly."""
    message_container("Hello", "user", "10:00 AM")
    mock_markdown.assert_called_once()
    call_args = mock_markdown.call_args
    assert "dbeafe" in str(call_args)  # COLOR_USER_BG
    assert "flex-end" in str(call_args)  # right-aligned


@patch("streamlit.markdown")
def test_message_container_assistant_message(mock_markdown):
    """Test message_container renders assistant messages correctly."""
    message_container("Response", "assistant", "10:01 AM")
    mock_markdown.assert_called_once()
    call_args = mock_markdown.call_args
    assert COLOR_PRIMARY in str(call_args)  # Primary border color
    assert "flex-start" in str(call_args)  # left-aligned


@patch("streamlit.markdown")
def test_message_container_system_message(mock_markdown):
    """Test message_container renders system messages correctly."""
    message_container("System notification", "system")
    mock_markdown.assert_called_once()
    call_args = mock_markdown.call_args
    assert "center" in str(call_args)  # centered
