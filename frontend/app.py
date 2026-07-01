import streamlit as st

from frontend.services.session import ROLE_OPTIONS, get_active_role, set_active_role


st.set_page_config(
    page_title="MCP Gateway Agents",
    page_icon=":bar_chart:",
    layout="wide",
)

st.title("MCP Gateway + Agentic Crypto Risk Platform")
st.caption("Phase 1 frontend shell with demo login and role-switch entry.")

with st.sidebar:
    st.subheader("Demo Access")
    selected_role = st.selectbox("Choose role", ROLE_OPTIONS, index=ROLE_OPTIONS.index(get_active_role()))
    if st.button("Enter Workspace", use_container_width=True):
        set_active_role(selected_role)
        st.success(f"Active role set to: {selected_role}")

st.markdown("### Current Focus")
st.write(
    "This project-owned frontend will become the single entrypoint for chat, dashboards, "
    "risk scoring, alerts, and audit review."
)

st.markdown("### Phase 1 Modules")
col1, col2, col3 = st.columns(3)
col1.info("Backend health app and route skeleton are ready for API expansion.")
col2.info("Integration contracts are in place for trade and risk source adapters.")
col3.info("Initial SQL migrations define the first schemas and core operational tables.")

st.markdown("### Demo Session")
st.write(f"Active role: `{get_active_role()}`")
st.write(
    "Use the pages in the left navigation as placeholders for the future login, dashboard, "
    "and operations experience."
)

