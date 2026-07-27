"""External Services Status tab UI with MCP/Tavily integration."""

from datetime import datetime

import streamlit as st
from src.mcp_integration import MCPIntegration, STATUS_SOURCES
from src.ui.components import header_card, info_box, COLOR_SUCCESS

SERVICE_ICONS = {
    "AWS": "🟧",
    "GCP": "🔵",
    "Azure": "🔷",
    "Google": "🟢",
}

EXCERPT_LENGTH = 220


def _trusted_domain_pill(domain: str) -> str:
    """Small pill showing which official domain this result was verified against."""
    return (
        f"<span style='background:{COLOR_SUCCESS}1a;color:{COLOR_SUCCESS};"
        f"border:1px solid {COLOR_SUCCESS}55;padding:2px 10px;border-radius:999px;"
        f"font-size:0.75em;font-weight:600;white-space:nowrap;'>✓ {domain}</span>"
    )


def _render_service_card(service: str, result: dict) -> None:
    """Render a single service's status as a clean, compact card."""
    icon = SERVICE_ICONS.get(service, "☁️")

    with st.container(border=True):
        if "error" in result:
            st.markdown(f"##### {icon} {service}")
            info_box(result["error"], "error")
            return

        domains = result.get("domains", [])
        top_left, top_right = st.columns([0.6, 0.4])
        with top_left:
            st.markdown(f"##### {icon} {service}")
        with top_right:
            if domains:
                st.markdown(
                    f"<div style='text-align:right;padding-top:6px'>{_trusted_domain_pill(domains[0])}</div>",
                    unsafe_allow_html=True,
                )

        results = result.get("results", [])
        if not results:
            info_box("No current reports found on the official status page.", "info")
            st.markdown(f"[🔗 Open official status page]({result.get('fallback_url', '#')})")
            return

        primary = results[0]
        st.markdown(f"**{primary.get('title') or 'Status update'}**")
        content = (primary.get("content") or "").strip()
        if content:
            excerpt = content[:EXCERPT_LENGTH].strip()
            if len(content) > EXCERPT_LENGTH:
                excerpt += "..."
            st.caption(excerpt)
        if primary.get("url"):
            st.markdown(f"[🔗 View source]({primary['url']})")

        remaining = results[1:]
        if remaining:
            with st.expander(f"More reports ({len(remaining)})"):
                for r in remaining:
                    title = r.get("title") or "Untitled report"
                    url = r.get("url")
                    st.markdown(f"- [{title}]({url})" if url else f"- {title}")

        st.caption(f"Source: {result.get('source', 'N/A')}")


def render_external_services_tab():
    """Render the External Services Status tab using MCP Tavily search."""
    header_card(
        "Cloud Services Status",
        "Live status pulled directly from each provider's own official status page"
    )
    st.divider()

    if "mcp_integration" not in st.session_state:
        try:
            st.session_state.mcp_integration = MCPIntegration()
        except (ValueError, RuntimeError) as e:
            info_box(f"Failed to initialize Tavily integration: {str(e)}", "error")
            info_box("Please ensure TAVILY_API is set in your .env file.", "info")
            return

    services = ["AWS", "GCP", "Azure", "Google"]
    control_left, control_right = st.columns([0.75, 0.25])
    with control_left:
        selected_services = st.multiselect(
            "Select services to check:",
            services,
            default=services,
            help="Select which services you want to check for current status",
            label_visibility="collapsed",
        )
    with control_right:
        refresh_clicked = st.button("🔄 Refresh", use_container_width=True)

    if refresh_clicked or "last_checked" not in st.session_state:
        st.session_state.last_checked = datetime.now().strftime("%H:%M:%S")

    if selected_services:
        st.caption(f"Last checked: {st.session_state.last_checked}")

        with st.spinner("🔍 Fetching service status..."):
            cols = st.columns(2)
            for idx, service in enumerate(selected_services):
                with cols[idx % 2]:
                    result = st.session_state.mcp_integration.get_service_status(service)
                    _render_service_card(service, result)

    st.divider()

    with st.expander("ℹ️ How it works"):
        info_box(
            "This tab uses **Tavily Search** (via MCP) restricted to each provider's "
            "own official status domain — no third-party aggregators.",
            "info"
        )
        st.markdown(
            "\n".join(
                f"- **{src['label']}**: `{'`, `'.join(src['domains'])}`"
                for src in STATUS_SOURCES.values()
            )
        )
