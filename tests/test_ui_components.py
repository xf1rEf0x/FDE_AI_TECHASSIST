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
