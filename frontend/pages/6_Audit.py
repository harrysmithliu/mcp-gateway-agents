import streamlit as st

from frontend.components.auth import render_api_error, require_authenticated_session
from frontend.services.api import ApiError
from frontend.services.audit import list_audit_events, list_tool_invocations


st.set_page_config(page_title="Audit Review", page_icon=":bookmark_tabs:", layout="wide")
token, user = require_authenticated_session()

st.title("Audit and Evidence Review")
st.caption(
    f"Reviewable evidence trail for {user.get('display_name', user.get('username', 'user'))}."
)

filter_col1, filter_col2, filter_col3 = st.columns(3)
with filter_col1:
    event_type = st.text_input("Event type", value="")
with filter_col2:
    session_id = st.text_input("Session ID", value="")
with filter_col3:
    tool_name = st.text_input("Tool name", value="")

if st.button("Load Audit Review", use_container_width=True):
    try:
        st.session_state["audit_events"] = list_audit_events(
            event_type=event_type or None,
            session_id=session_id or None,
            access_token=token,
        )
        st.session_state["audit_tool_calls"] = list_tool_invocations(
            tool_name=tool_name or None,
            session_id=session_id or None,
            access_token=token,
        )
    except ApiError as exc:
        render_api_error(exc)

audit_events = st.session_state.get("audit_events", {})
audit_tool_calls = st.session_state.get("audit_tool_calls", {})

event_col, tool_col = st.columns(2)
with event_col:
    st.markdown("#### Audit events")
    st.dataframe(audit_events.get("events", []), use_container_width=True)
with tool_col:
    st.markdown("#### Tool invocations")
    st.dataframe(audit_tool_calls.get("tool_calls", []), use_container_width=True)

if audit_events or audit_tool_calls:
    st.markdown("#### Evidence notes")
    st.info(
        "Use event IDs, session IDs, tool names, and recorded payloads as the traceable "
        "references for an investigation or approval decision."
    )
