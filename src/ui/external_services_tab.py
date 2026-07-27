"""External Services Status tab UI with MCP/Tavily integration."""

import streamlit as st
from src.mcp_integration import MCPIntegration
from src.ui.components import header_card, status_badge, info_box


def render_external_services_tab():
    """Render the External Services Status tab using MCP Tavily search."""
    # Header with description
    header_card(
        "Cloud Services Status",
        "Real-time status of major cloud providers"
    )

    # Initialize MCP integration
    if "mcp_integration" not in st.session_state:
        try:
            st.session_state.mcp_integration = MCPIntegration()
        except (ValueError, RuntimeError) as e:
            info_box(f"Failed to initialize Tavily integration: {str(e)}", "error")
            info_box("Please ensure TAVILY_API is set in your .env file.", "info")
            return

    # Service selector
    services = ["AWS", "GCP", "Azure", "Google"]
    selected_services = st.multiselect(
        "Select services to check:",
        services,
        default=services,
        help="Select which services you want to check for current status"
    )

    if st.button("🔄 Refresh Status", use_container_width=True):
        st.session_state.refresh_status = True

    # Check and display status
    if selected_services or st.session_state.get("refresh_status"):
        st.session_state.refresh_status = False

        with st.spinner("🔍 Fetching service status..."):
            # Display services in columns for better scanability
            cols = st.columns(2)
            col_idx = 0

            for service in selected_services:
                with cols[col_idx % 2]:
                    result = st.session_state.mcp_integration.get_service_status(service)

                    if "error" in result:
                        info_box(result["error"], "error")
                    else:
                        # Determine status based on result
                        status_items = result.get("status", [])
                        has_incidents = not isinstance(status_items, list) or (
                            isinstance(status_items, list) and any("No incidents" not in str(item) for item in status_items if item)
                        )
                        status = "degraded" if has_incidents else "operational"

                        # Display status badge in card-like container
                        st.markdown(f"**{status_badge(service, status)}**")

                        # Display detailed status information
                        if isinstance(status_items, list) and status_items:
                            for item in status_items:
                                if item:  # Skip empty items
                                    if "No incidents" in str(item):
                                        info_box(str(item), "success")
                                    else:
                                        st.markdown(str(item))
                        else:
                            st.write(status_items)

                        st.caption(f"Source: {result.get('source', 'N/A')}")

                col_idx += 1

    # Info section with component
    with st.expander("ℹ️ How it works"):
        info_box(
            "This tab uses **Tavily Search** (via MCP integration) to query real-time status information from major cloud providers.",
            "info"
        )
        st.markdown("""
        **Status Sources:**
        - **AWS**: https://status.aws.amazon.com/
        - **GCP**: https://status.cloud.google.com/
        - **Azure**: https://status.azure.com/
        - **Google**: https://www.google.com/appsstatus/

        Results are pulled from the latest available status pages and incident reports.
        """)
