# TechAssist AI Design System

**Version:** 1.0  
**Last Updated:** 2026-07-27  
**Status:** Complete

This document defines the component library, color system, spacing rules, and usage guidelines for the TechAssist AI application. All UI elements must follow this design system to ensure consistency, accessibility, and maintainability.

---

## Quick Start

All UI components are defined in `src/ui/components.py`. Import and use them in any tab or page:

```python
from src.ui.components import (
    header_card,
    info_box,
    message_container,
    action_card,
    status_badge,
    form_group,
    metric_tile,
    sidebar_section
)
```

---

## Components

### header_card(title, description, action_button)

Renders a section header with optional description and optional action button.

**Purpose:** Introduce major sections with clear hierarchy and optional CTA.

**Parameters:**
- `title` (str): Bold section heading text
- `description` (str, optional): Italic secondary text below title
- `action_button` (tuple, optional): Tuple of `(button_text, button_key, button_help)`

**Example:**
```python
header_card(
    "Chat with IT Support",
    "Ask questions about IT issues, get instant help"
)

header_card(
    "Help Desk",
    "Create tickets, request software, or check your assets",
    action_button=("Clear History", "clear_btn", "Remove all messages")
)
```

**Usage Rules:**
1. Use for every major tab or section header
2. Always include a description to explain section purpose
3. Action button is optional; use only if you have a primary CTA for the section
4. Do not nest header_cards

---

### status_badge(label, status)

Returns a colored status indicator with emoji prefix.

**Purpose:** Visually indicate operational state of a service or user role.

**Parameters:**
- `label` (str): Display text (e.g., "AWS", "Operational")
- `status` (str): One of `"operational"`, `"degraded"`, `"down"`, `"pending"`, `"completed"`

**Return:** Formatted string with emoji and label (e.g., "✅ Operational")

**Status Mapping:**
- `"operational"` → ✅ Green
- `"degraded"` → ⚠️ Yellow
- `"down"` → ❌ Red
- `"pending"` → ⏳ Gray
- `"completed"` → ✓ Green

**Example:**
```python
# Service status
st.markdown(status_badge("AWS", "operational"))
st.markdown(status_badge("Azure", "degraded"))

# User role badge
st.markdown(status_badge(user_role.capitalize(), "completed"))
```

**Usage Rules:**
1. Use for service status indicators and role badges
2. Always use the predefined status values; map custom states to these five
3. Pair with `info_box()` for additional context
4. Use in table rows, lists, or metric displays

---

### action_card(title, description, icon, key)

Renders a clickable card for primary user actions (quick templates, workflows).

**Purpose:** Present actionable items in an inviting, card-based format.

**Parameters:**
- `title` (str): Card title (visible at all times)
- `description` (str): Card description (smaller text)
- `icon` (str): Emoji icon (e.g., "📋", "💾", "🖥️")
- `key` (str): Unique Streamlit key for button state

**Return:** Boolean (True if clicked, False otherwise)

**Example:**
```python
if action_card(
    "Create Ticket",
    "Report an issue",
    "📋",
    "quick_create_ticket"
):
    st.session_state.user_input = "I need to create a support ticket"
    st.rerun()

if action_card(
    "Request Software",
    "Install new software",
    "💾",
    "quick_software_request"
):
    st.session_state.user_input = "I need to request software"
    st.rerun()
```

**Usage Rules:**
1. Use for quick templates and high-priority user workflows
2. Render action cards in columns (typically 3 per row)
3. Hide cards once the user starts interacting (e.g., first message sent)
4. Always provide icon + title + description
5. Pre-fill input fields or navigate on click

---

### message_container(content, role, timestamp)

Renders a single chat message with styling based on sender role.

**Purpose:** Display chat messages with consistent, role-aware styling.

**Parameters:**
- `content` (str): Message text (supports markdown)
- `role` (str): One of `"user"`, `"assistant"`, `"system"`
- `timestamp` (str, optional): Timestamp to display (e.g., "2:45 PM")

**Message Styling by Role:**
- **User:** Right-aligned, light blue background (#dbeafe), dark text
- **Assistant:** Left-aligned, white background, left blue border (#0066cc)
- **System:** Center-aligned, light gray background, muted text

**Example:**
```python
# Render all messages in conversation history
for message in st.session_state.messages:
    message_container(message["content"], message["role"], message.get("timestamp"))

# Or render individual messages
message_container("Hello, how can I help?", "assistant")
message_container("I need to reset my password", "user", timestamp="2:45 PM")
message_container("Password reset requested", "system")
```

**Usage Rules:**
1. Use for all chat and conversation UI (not notifications)
2. Always include the role parameter to ensure correct styling
3. Timestamp is optional; include if conversation history spans time
4. Do not style messages with raw HTML; use this component
5. Markdown is supported in content

---

### info_box(message, severity, dismissible)

Displays a color-coded alert box with emoji and optional dismiss button.

**Purpose:** Present alerts, confirmations, errors, and informational messages consistently.

**Parameters:**
- `message` (str): Alert message text (supports markdown)
- `severity` (str): One of `"info"`, `"success"`, `"warning"`, `"error"`
- `dismissible` (bool, optional): If True, note that Streamlit does not natively support dismissal in alerts; document for future implementation

**Severity Mapping:**
- `"info"` → ℹ️ Blue background (informational)
- `"success"` → ✅ Green background (action completed)
- `"warning"` → ⚠️ Yellow background (user attention needed)
- `"error"` → ❌ Red background (error occurred)

**Example:**
```python
# Login error
info_box("Invalid email or password.", "error")

# Success confirmation
info_box("Ticket #1234 created successfully!", "success")

# Informational message
info_box("Your password will expire in 7 days.", "warning")

# Help text
info_box("Use this tab to manage software requests.", "info")

# Markdown support
info_box("""**Important:** 
- Update your password regularly
- Enable multi-factor authentication
- Report suspicious activity""", "warning")
```

**Usage Rules:**
1. **Never use** raw `st.error()`, `st.warning()`, `st.success()`, or `st.info()`
2. Always use `info_box()` for all alerts and notifications
3. Choose severity that matches the message urgency
4. Use markdown for formatting within messages
5. Place alerts near the action they relate to (login errors near login form, etc.)
6. For dismissible behavior, manage visibility in `st.session_state`

---

### form_group(label, input_type, help_text, key, **kwargs)

Wraps an input field with consistent label, help text, and spacing.

**Purpose:** Standardize form field presentation across the app.

**Parameters:**
- `label` (str): Bold field label text
- `input_type` (str): One of `"text"`, `"password"`, `"textarea"`, `"number"`
- `help_text` (str, optional): Small caption text below input
- `key` (str, optional): Streamlit widget key for state tracking
- `**kwargs`: Additional arguments passed to underlying Streamlit widget (e.g., `placeholder`, `max_chars`)

**Return:** The input value entered by the user

**Example:**
```python
with st.form("login_form"):
    email = form_group(
        "Email",
        "text",
        help_text="e.g., alice@techassist.com",
        key="login_email",
        placeholder="Enter your email"
    )
    password = form_group(
        "Password",
        "password",
        help_text="Enter your password",
        key="login_password"
    )
    submitted = st.form_submit_button("Login")

# Textarea example
description = form_group(
    "Describe your issue",
    "textarea",
    help_text="Be as detailed as possible",
    key="issue_description",
    height=200
)
```

**Usage Rules:**
1. Use for all form inputs (text, password, number, textarea)
2. Always provide a clear label
3. Include help_text if the field purpose is not obvious
4. Use within `st.form()` for grouped submission
5. Never use raw `st.text_input()` or `st.text_area()` directly

---

### metric_tile(title, value, icon, subtitle)

Displays a key metric (stat tile) with optional icon and subtitle.

**Purpose:** Highlight important metrics or KPIs in a visually distinct format.

**Parameters:**
- `title` (str): Metric name (e.g., "Active Sessions")
- `value` (str): Metric value, typically numeric (e.g., "42")
- `icon` (str, optional): Emoji icon (e.g., "💬")
- `subtitle` (str, optional): Additional text below value (e.g., "Last 24 hours")

**Example:**
```python
col1, col2, col3 = st.columns(3)
with col1:
    metric_tile("Active Sessions", "12", icon="💬", subtitle="Real-time")
with col2:
    metric_tile("Pending Tickets", "5", icon="🎫", subtitle="Assigned to you")
with col3:
    metric_tile("Success Rate", "98%", icon="✅", subtitle="Last 30 days")
```

**Usage Rules:**
1. Use in dashboard or summary sections
2. Always place within columns for grid layout
3. Icon is optional; use if it enhances understanding
4. Subtitle is optional; use for context (time period, etc.)
5. Use for display only; not interactive

---

### sidebar_section(title, content_func, expanded)

Renders a consistently-styled sidebar section with title and divider.

**Purpose:** Organize sidebar content into logical sections.

**Parameters:**
- `title` (str): Section title to display in the sidebar
- `content_func` (callable): Function that renders the section's content (called within sidebar context)
- `expanded` (bool, optional): If True, section is visible; Streamlit does not have native collapsible sections

**Example:**
```python
def render_settings():
    st.session_state.theme = st.selectbox(
        "Theme:",
        ["Light", "Dark"]
    )
    st.session_state.language = st.selectbox(
        "Language:",
        ["English", "Spanish", "French"]
    )

def render_quick_links():
    st.markdown("[FAQ](https://example.com/faq)")
    st.markdown("[Support](https://example.com/support)")
    st.markdown("[Documentation](https://example.com/docs)")

# Use in app
sidebar_section("⚙️ Settings", render_settings)
sidebar_section("🔗 Quick Links", render_quick_links)
```

**Usage Rules:**
1. Use for all sidebar sections
2. Always provide a title with emoji
3. Pass a callable function (not a rendered element)
4. Do not nest sidebar_sections
5. Divider is automatically added below each section

---

## Color System

The color palette is defined in `src/ui/components.py` and should be imported for use in any styled HTML or markdown.

### Color Constants

```python
COLOR_PRIMARY = "#0066cc"      # Blue - Primary actions, borders
COLOR_SUCCESS = "#10b981"      # Green - Success states, operational
COLOR_WARNING = "#f59e0b"      # Amber - Warnings, degraded states
COLOR_ERROR = "#ef4444"        # Red - Errors, down states
COLOR_NEUTRAL = "#6b7280"      # Gray - Secondary text
COLOR_SURFACE = "#f9fafb"      # Off-white - System message background
COLOR_USER_BG = "#dbeafe"      # Light blue - User message background
```

### Color Usage Guidelines

| Color | Component | Usage |
|-------|-----------|-------|
| **PRIMARY** | info_box, message_container, status_badge | Primary action, primary border, selected state |
| **SUCCESS** | info_box, status_badge, metric_tile | Success confirmation, operational status, completed action |
| **WARNING** | info_box, status_badge | Warnings, degraded service, user attention needed |
| **ERROR** | info_box, status_badge | Errors, service down, action failed |
| **NEUTRAL** | All text components | Secondary text, helper text, timestamps, captions |
| **SURFACE** | message_container | System message background |
| **USER_BG** | message_container | User message background |

### Adding Custom Colors

If a new color is needed:
1. Add constant to `src/ui/components.py`
2. Document in this file
3. Justify the addition (must not duplicate existing palette)
4. Obtain product/design approval before merging

---

## Spacing Unit

All spacing uses a base unit of 12 pixels. Scale in multiples:

```python
SPACING_UNIT = 12       # Base unit
SPACING_SM = 12         # 1x - Single spacing
SPACING_MD = 24         # 2x - Double spacing
SPACING_LG = 36         # 3x - Triple spacing
SPACING_XL = 48         # 4x - Quad spacing
```

### Spacing Usage

| Element | Spacing |
|---------|---------|
| Padding within cards | SPACING_MD (24px) |
| Margin between sections | SPACING_LG (36px) |
| Margin between components | SPACING_MD (24px) |
| Margin between message items | SPACING_SM (12px) |
| Sidebar section spacing | SPACING_MD (24px) |

### Dividers

Use `st.divider()` to separate major sections:
- After `header_card()` in any major section
- Between main content areas
- Before footer/info sections

---

## Usage Guidelines

### Rule 1: Always Use Components

**Do:**
```python
info_box("Password reset successful!", "success")
header_card("My Section", "Description")
message_container("Hello!", "assistant")
```

**Don't:**
```python
st.success("Password reset successful!")
st.markdown("## My Section")
st.write("Hello!")
```

### Rule 2: Use info_box() for All Alerts

**Do:**
```python
try:
    result = some_action()
except ValueError as e:
    info_box(f"Action failed: {str(e)}", "error")
```

**Don't:**
```python
try:
    result = some_action()
except ValueError as e:
    st.error(f"Action failed: {str(e)}")
```

### Rule 3: Use header_card() for Section Titles

**Do:**
```python
header_card("Chat with IT Support", "Ask questions about IT issues")
st.divider()
# ... section content ...
```

**Don't:**
```python
st.markdown("## Chat with IT Support")
st.markdown("*Ask questions about IT issues*")
# ... section content ...
```

### Rule 4: Use message_container() for Chat UI

**Do:**
```python
for message in st.session_state.messages:
    message_container(message["content"], message["role"])
```

**Don't:**
```python
for message in st.session_state.messages:
    if message["role"] == "user":
        st.chat_message("user").write(message["content"])
    else:
        st.chat_message("assistant").write(message["content"])
```

### Rule 5: Use ACTION_CARDs for Quick Workflows

**Do:**
```python
if action_card("Create Ticket", "Report an issue", "📋", "create_ticket_btn"):
    st.session_state.user_input = "I need to create a ticket"
    st.rerun()
```

**Don't:**
```python
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("📋 Create Ticket\n_Report an issue_"):
        st.session_state.user_input = "I need to create a ticket"
        st.rerun()
```

### Rule 6: No Hardcoded Colors

**Do:**
```python
from src.ui.components import COLOR_PRIMARY
st.markdown(f"<span style='color: {COLOR_PRIMARY};'>Active</span>", unsafe_allow_html=True)
```

**Don't:**
```python
st.markdown("<span style='color: #0066cc;'>Active</span>", unsafe_allow_html=True)
```

### Rule 7: Consistent Form Inputs

**Do:**
```python
with st.form("my_form"):
    username = form_group("Username", "text", help_text="Enter your username")
    password = form_group("Password", "password", help_text="Enter your password")
    submitted = st.form_submit_button("Login")
```

**Don't:**
```python
username = st.text_input("**Username**", help="Enter your username")
password = st.text_input("**Password**", type="password", help="Enter your password")
submitted = st.button("Login", use_container_width=True)
```

---

## Component Library Demo

To view all components in action, run:

```bash
streamlit run src/ui/components.py
```

This will launch a demo page showing every component with example usage.

---

## Future Enhancements

### Planned Features (Not Yet Implemented)

- **Dark mode support:** Add `COLOR_*_DARK` constants and mode toggle
- **Custom theme switching:** Allow users to select brand colors from settings
- **Keyboard shortcuts:** Add keyboard navigation for accessibility
- **Dashboard metrics view:** Expanded metric_tile with chart integration
- **Collapsible sidebar sections:** Native Streamlit support or custom expander
- **Toast notifications:** Brief, dismissible alerts for non-critical messages
- **Responsive grid:** Automatic column adjustment based on viewport width

### Adding New Components

When proposing new components:
1. Verify it doesn't duplicate existing functionality
2. Follow the same naming and parameter conventions
3. Document in this file with usage examples
4. Add a demo section in `src/ui/components.py::demo_components()`
5. Create unit tests in `tests/test_ui_components.py`
6. Update this documentation

---

## Testing

All components have unit tests in `tests/test_ui_components.py`:

```bash
pytest tests/test_ui_components.py -v
```

When modifying components:
1. Run tests to verify no regressions
2. Update tests if component signature changes
3. Add tests for new components

---

## Troubleshooting

### Message Not Displaying Correctly

**Problem:** Messages not styled as user/assistant  
**Solution:** Ensure `role` parameter is one of: `"user"`, `"assistant"`, `"system"`

### Color Looks Wrong

**Problem:** Color doesn't match design  
**Solution:** Always use COLOR_* constants, not hex values. Check constant value in `src/ui/components.py`

### Components Not Rendering

**Problem:** Component not showing up  
**Solution:** 
1. Verify it's imported from `src.ui.components`
2. Check function signature against this documentation
3. Ensure you're not inside a container that's hidden (e.g., `st.expander` that's closed)

### Spacing Is Off

**Problem:** Layout doesn't match design  
**Solution:** 
1. Use SPACING_* constants for margins/padding
2. Use columns for layout, not raw markdown
3. Add `st.divider()` between major sections

---

## Support & Questions

For design system questions or proposals:
1. Check this documentation first
2. Review `src/ui/components.py` source code
3. Check existing issues in the project repository
4. Propose new components via pull request with documentation update

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-07-27 | Initial design system documentation. All 8 components documented. Color system defined. Usage guidelines established. |

---

## Appendix A: Component Summary Table

| Component | Purpose | Params | Return | Use When |
|-----------|---------|--------|--------|----------|
| `header_card` | Section headers | title, description, action_button | None | Starting a new major section |
| `status_badge` | Status indicators | label, status | str | Showing service/role status |
| `action_card` | Clickable action cards | title, description, icon, key | bool | Quick workflows, templates |
| `message_container` | Chat messages | content, role, timestamp | None | Displaying messages |
| `info_box` | Alerts & notifications | message, severity, dismissible | None | All alerts/confirmations |
| `form_group` | Form inputs | label, input_type, help_text, key | Any | Form fields |
| `metric_tile` | Statistics display | title, value, icon, subtitle | None | Dashboards, metrics |
| `sidebar_section` | Sidebar organization | title, content_func, expanded | None | Organizing sidebar |

---

**End of Design System Documentation**
