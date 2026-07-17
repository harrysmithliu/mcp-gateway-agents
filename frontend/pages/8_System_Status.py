import streamlit as st

from frontend.components.auth import render_api_error, require_authenticated_session
from frontend.services.api import ApiError
from frontend.services.runtime_status import get_admin_runtime_status
from frontend.services.session import get_auth_roles


st.set_page_config(page_title="System Status", page_icon=":bar_chart:", layout="wide")
token, user = require_authenticated_session()

if "admin" not in get_auth_roles():
    st.error("System status requires the admin role.")
    st.stop()

st.title("System Status")
st.caption(
    f"Read-only operational visibility for {user.get('display_name', user.get('username', 'admin'))}."
)

try:
    status = get_admin_runtime_status(access_token=token)
except ApiError as exc:
    render_api_error(exc)
    st.stop()

readiness = status.readiness
st.metric("Overall readiness", readiness.get("state", "unknown"))
st.caption(f"Environment: `{status.environment}` · Observed: `{status.observed_at}`")

st.markdown("#### Runtime components")
components = readiness.get("components", [])
if components:
    st.dataframe(components, use_container_width=True, hide_index=True)
else:
    st.info("No runtime component details were returned.")

mode_col, migration_col, mcp_col = st.columns(3)
with mode_col:
    st.markdown("#### Runtime mode")
    st.json(status.runtime_mode)
with migration_col:
    st.markdown("#### Migration status")
    st.json(status.migration)
with mcp_col:
    st.markdown("#### MCP visibility")
    st.json(status.mcp)
