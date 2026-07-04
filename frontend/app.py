import streamlit as st

from frontend.services.chat import ChatApiResponse, post_chat_message
from frontend.services.session import ROLE_OPTIONS, get_active_role, set_active_role


st.set_page_config(
    page_title="MCP Gateway Agents",
    page_icon=":bar_chart:",
    layout="wide",
)

st.title("Trading and Risk Agentic Platform")
st.caption("Frontend shell with demo login and role-switch entry.")

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

st.markdown("### Current Modules")
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

st.markdown("### Demo Chat")
default_prompt = "Review this account for trade risk and recommend next steps."

with st.form("demo_chat_form"):
    message_text = st.text_area("Message", value=default_prompt, height=120)
    submitted = st.form_submit_button("Send To Chat API", use_container_width=True)

if submitted:
    try:
        chat_response: ChatApiResponse = post_chat_message(
            user_role=get_active_role(),
            message_text=message_text,
        )
        st.success("Chat response received.")
        st.write(chat_response.reply_text)

        if chat_response.tool_names:
            st.caption("Suggested tools")
            st.write(chat_response.tool_names)

        if chat_response.evidence:
            st.caption("Evidence")
            st.write(chat_response.evidence)

        if chat_response.actions:
            st.caption("Actions")
            st.write(chat_response.actions)
    except RuntimeError as exc:
        st.error(str(exc))
