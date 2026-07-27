# TechAssist AI — Professional UI Redesign Specification

**Date:** 2026-07-27  
**Objective:** Redesign the TechAssist AI application UI for professional quality, clean aesthetics, reduced cognitive load, and consistent information hierarchy across all three tabs (Chat, HelpDesk, External Services).

**Design Principles:**
- Clean, minimalist aesthetic with purposeful use of space
- Single design system across all pages and features
- Information hierarchy that guides users to their next action
- Native Streamlit components only (no custom CSS/HTML)
- Fast task completion through simplified workflows

---

## 1. Component Utility Library (`src/ui/components.py`)

A new module that provides reusable, styled components enforcing visual consistency across the app. Components are Python functions that return Streamlit elements wrapped with consistent styling, spacing, and semantics.

### Color System

| Role | Color | Hex | Usage |
|------|-------|-----|-------|
| Primary Action | Blue | `#0066cc` | Buttons, primary CTAs |
| Success | Green | `#10b981` | Confirmations, operational status |
| Warning | Amber | `#f59e0b` | Cautions, degraded status |
| Error | Red | `#ef4444` | Failures, down status |
| Neutral/Secondary | Gray | `#6b7280` | Secondary text, dividers |
| Surface/Background | Off-white | `#f9fafb` | Card backgrounds, sections |

### Spacing Unit
12px base unit. Margins and padding scale in multiples: 12px, 24px, 36px, 48px.

### Component Library

**`header_card(title: str, description: str = None, action_button: tuple = None)`**
- Renders a section header with optional description and action button
- Used for each tab's main heading
- Returns: Streamlit column layout with title, description, and button

**`status_badge(label: str, status: str)`**
- status ∈ {"operational", "degraded", "down", "pending", "completed"}
- Color-coded dot + label
- Returns: small Streamlit metric or expander title component

**`form_group(label: str, input_func, help_text: str = None)`**
- Wraps input field with label, help text, and consistent spacing
- Reduces boilerplate in forms
- Returns: formatted form section

**`metric_tile(title: str, value: str, icon: str = "", subtitle: str = None)`**
- Displays a key stat (e.g., "3 Active Sessions", "5 Pending Requests")
- Used on dashboard/summary views
- Returns: Streamlit container with styled metric

**`action_card(title: str, description: str, icon: str, on_click: callable, key: str)`**
- Clickable card for primary user actions (e.g., "Create Ticket", "Request Software")
- Shows icon + title + description
- Returns: interactive Streamlit button styled as a card

**`message_container(content: str, role: str, timestamp: str = None)`**
- Renders a single chat message with consistent styling
- role ∈ {"user", "assistant", "system"}
- User messages: right-aligned, light blue background
- Assistant messages: left-aligned, neutral background
- Returns: Streamlit container with message

**`info_box(message: str, severity: str, dismissible: bool = False)`**
- severity ∈ {"info", "warning", "error", "success"}
- Color-coded box with icon
- Returns: Streamlit alert component

**`sidebar_section(title: str, content_func, expanded: bool = True)`**
- Wraps sidebar content with header and consistent dividers
- Returns: Streamlit expander or container

---

## 2. Login Flow — Clean Entry Point

### Layout
- Center the login card on the screen (narrow width, ~400px)
- Brand message: "🤖 TechAssist AI" (larger)
- Tagline: "IT Support, Simplified"
- Email + password form (standard inputs)
- Submit button (full-width, primary blue)

### Messaging
- Demo credentials shown in a subtle info box *only on first load* (no clutter after login attempt)
- Success/error messages use `info_box()` component with appropriate severity
- Avoid showing role-specific UI before login completes

### Component Updates
- Replace current `st.title()` + `st.markdown()` with brand card
- Use `form_group()` for email/password inputs
- Use `info_box()` for all alerts

---

## 3. Main Navigation & Sidebar — Single Source of Truth

### Sidebar Layout (top to bottom)

**User Card**
- Shows: "Logged in as {Name}" + Role badge (using `status_badge()`)
- Logout button (secondary style)

**Divider** (horizontal line, gray)

**Settings Section** (using `sidebar_section()`)
- LLM Provider selector (HuggingFace / Gemini)
- Provider info box (e.g., "🤖 Using HuggingFace: DeepSeek-R1")
- Temperature slider (keep existing UI)

**Divider**

**About Your Role** (expander, optional)
- Show role description (keep existing content)

**Divider**

**Session History** (using `sidebar_section()`)
- List saved sessions in compact format:
  - Session name (truncated to 40 chars)
  - Delete button (🗑️)
  - No separate columns, just: "[Load button] [Delete button]"
- Total session count at bottom
- Empty state message: "💬 Start a conversation to create a session"

**Divider**

**New Chat Button** (primary blue, full-width)
- Clear the conversation and start fresh

### Main Content
- Tab order: "💬 AI Chat" → "🎫 HelpDesk" → (if engineer) "☁️ External Services"
- Tab styling: use Streamlit native tabs (already clean, no changes needed)
- Each tab has its own subheader using `header_card()`

---

## 4. Chat Tab — Conversational Clarity

### Layout (top to bottom)

**Header**
- `header_card("Chat with IT Support", "Ask questions about IT issues, get instant help")`
- Optional: show provider + temperature as subtle badges

**Message Area**
- Display all messages using `message_container()` component
- User messages: right-aligned, light blue background (`#dbeafe`)
- Assistant messages: left-aligned, white/neutral background
- Clear visual separation between consecutive messages (12px margin)

**Quick Templates** (shown only when conversation is empty)
- "Quick questions for your role:"
- Display templates as grid of action cards (3 columns)
- Each card: title + icon, clickable
- Hide once first message is sent

**Input Area**
- `st.chat_input()` styled with icon hint
- Placeholder: "Ask me anything about IT support..."

**Processing State**
- Keep spinner: "🤔 Thinking..." (existing, clear)

### Data Flow
- Messages persist in `st.session_state.messages`
- Session auto-created on first assistant response
- Session auto-saved after each interaction

---

## 5. HelpDesk Tab — Task-Driven Layout

### Layout (top to bottom)

**Header**
- `header_card("Help Desk", "Create tickets, request software, or check your assets")`

**Quick Actions Section** (only shown at tab start, before any conversation)
- Three large `action_card()` components in a grid:
  1. 📋 Create Ticket — "Report an issue or request support"
  2. 💾 Request Software — "Install or upgrade software on your device"
  3. 🖥️ Check Assets — "View your devices and warranty information"
- Cards are clickable; clicking pre-fills the chat input with intent (e.g., "I need to create a support ticket")

**Message Area**
- Same as Chat tab: all messages use `message_container()`
- Chat history scrolls naturally

**Input Area**
- `st.chat_input("Ask about tickets, software requests, or your assets...")`

**Processing State**
- Spinner: "🤔 Processing..."

**Admin Tools** (if user is admin, shown at bottom)
- Collapsible section: "🔑 Admin Tools"
- Message: "You have admin permissions for software request approvals."
- Link to Software Request feature

### Agent Routing (backend logic, no UI changes)
- Intent detection happens silently
- Routes to HelpDesk, Software, or Asset Search agent
- Response displayed as assistant message

---

## 6. External Services Tab — Scannable Status

### Layout (top to bottom)

**Header**
- `header_card("Cloud Services Status", "Real-time status of major cloud providers")`

**Controls**
- Multi-select: "Select services to check:" (AWS, GCP, Azure, Google — all selected by default)
- Refresh button: "🔄 Refresh Status" (primary blue, full-width)

**Status Display** (only shown if services selected)
- For each selected service, display a status card:
  - Service name (bold)
  - Status badge: color-coded dot + label ("Operational", "Degraded", "Down")
  - Last updated time
  - Expandable details (incidents, affected regions) — click to expand

**Status Card Details**
- Operational: green dot ✓
- Degraded: yellow dot ⚠️
- Down: red dot ✗
- Each card shows icon + status name

**Loading State**
- Spinner: "🔍 Fetching service status..."

**Info Section** (at bottom, collapsible)
- "ℹ️ How it works" expander
- Explain Tavily Search integration
- List service status page URLs

---

## 7. Error Handling & Edge Cases

### All Tabs
- Failed API calls: use `info_box()` with severity="error"
- Missing API keys: use `info_box()` with severity="warning" + actionable message
- Empty states: friendly message in `info_box()` with severity="info"

### Chat Tab
- No messages → show templates
- Failed response → error box + retry prompt

### HelpDesk Tab
- Intent unclear → ask clarification in assistant message
- Admin tools only visible if `is_admin()` returns True

### External Services Tab
- No services selected → show empty state message
- Tavily not initialized → error box with setup instructions

---

## 8. Typography & Text Styling

- **Page titles:** Streamlit `st.title()` (existing, no change)
- **Section headers:** `header_card()` function (bold, 18px equivalent)
- **Card titles:** Bold, 16px equivalent
- **Body text:** Regular, 14px equivalent
- **Help text / captions:** Gray (`#6b7280`), 12px equivalent
- **Code/system messages:** Monospace (existing Streamlit markdown)

---

## 9. Accessibility & Inclusive Design

- All buttons have clear labels (not just icons)
- Color is never the only indicator (add text + icons)
- Form inputs have associated labels (via `form_group()`)
- Alt text for icons/emojis via tooltips where applicable
- Sufficient contrast ratios (blue `#0066cc` on white passes WCAG AA)

---

## 10. Testing & Verification

### Manual Testing Checklist
- [ ] Login flow: form submission, error handling, demo credentials visibility
- [ ] Chat tab: message rendering, quick templates disappear after first message, auto-session creation
- [ ] HelpDesk tab: action cards appear, intent routing works, admin tools visible to admins only
- [ ] External Services tab: multi-select works, status cards render correctly, refresh button updates data
- [ ] Sidebar: session history loads, delete works, logout clears state
- [ ] Responsive: layout works on desktop (Streamlit's native responsiveness)

### Component Testing
- Each component in `components.py` has a demo function (e.g., `demo_status_badge()`)
- Run demos in isolation to verify styling

---

## 11. Implementation Phases

**Phase A: Component Library**
- Create `src/ui/components.py` with 8 core components
- Write demo functions for each component

**Phase B: Login Flow**
- Refactor `app.py` login section to use components

**Phase C: Sidebar & Navigation**
- Refactor sidebar in `app.py` to use `sidebar_section()` and other components

**Phase D: Chat Tab**
- Refactor message rendering to use `message_container()`
- Style quick templates as action cards

**Phase E: HelpDesk Tab**
- Refactor `src/ui/helpdesk_tab.py` to use components
- Add quick action cards section

**Phase F: External Services Tab**
- Refactor `src/ui/external_services_tab.py` to use components
- Style status display as cards with badges

**Phase G: Integration & Polish**
- Test all tabs end-to-end
- Verify consistency across all sections
- Adjust spacing/colors if needed

---

## 12. Success Criteria

- [ ] All three tabs use consistent color system, spacing, and component patterns
- [ ] Login page is clean and centered
- [ ] Chat messages are visually distinct (user vs. assistant)
- [ ] HelpDesk tab shows quick action cards at start
- [ ] External Services tab shows status as scannable cards
- [ ] No custom CSS or HTML — only Streamlit native components
- [ ] All error/warning messages use consistent alert styling
- [ ] Sidebar is well-organized with clear sections
- [ ] Users can complete common tasks (create ticket, request software, check status) without confusion

---

## 13. Future Enhancements (Out of Scope)

- Custom theming (light/dark mode toggle)
- Keyboard shortcuts for power users
- Dashboard view with metrics/analytics
- Advanced search/filtering in session history
- Mobile-optimized layout

