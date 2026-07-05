import streamlit as st

from frontend.services.chat import (
    ChatApiResponse,
    ChatApiToolInvocationResult,
    post_chat_message,
    post_knowledge_search,
    post_ops_create_alert_or_action,
    post_risk_score_account,
    post_trade_query_metrics,
)
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


def render_tool_invocation_result(
    title: str,
    tool_invocation_result: ChatApiToolInvocationResult,
) -> None:
    st.success(f"{title} response received.")
    st.write(
        f"`{tool_invocation_result.tool_name}` "
        f"[{tool_invocation_result.invocation_status}]"
    )
    st.code(
        {
            "request_payload": tool_invocation_result.request_payload,
            "response_payload": tool_invocation_result.response_payload,
        },
        language="python",
    )

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

        if chat_response.planned_tool_calls:
            st.caption("Planned Tool Calls")
            for planned_tool_call in chat_response.planned_tool_calls:
                st.write(
                    f"- `{planned_tool_call.tool_name}` "
                    f"({planned_tool_call.domain}): {planned_tool_call.description}"
                )

        if chat_response.tool_invocation_results:
            st.caption("Tool Invocation Results")
            for tool_invocation_result in chat_response.tool_invocation_results:
                st.write(
                    f"- `{tool_invocation_result.tool_name}` "
                    f"[{tool_invocation_result.invocation_status}]"
                )
                st.code(
                    {
                        "request_payload": tool_invocation_result.request_payload,
                        "response_payload": tool_invocation_result.response_payload,
                    },
                    language="python",
                )

        if chat_response.evidence:
            st.caption("Evidence")
            st.write(chat_response.evidence)

        if chat_response.actions:
            st.caption("Actions")
            st.write(chat_response.actions)
    except RuntimeError as exc:
        st.error(str(exc))

st.markdown("### Tool Debug Panel")
st.caption("Use the direct tool endpoints to inspect each tool result without routing through chat.")

tool_col1, tool_col2 = st.columns(2)

with tool_col1:
    with st.form("knowledge_search_form"):
        knowledge_query = st.text_area(
            "Knowledge Search Query",
            value="policy playbook case review",
            height=100,
        )
        knowledge_submitted = st.form_submit_button(
            "Run Knowledge Search",
            use_container_width=True,
        )

    if knowledge_submitted:
        try:
            knowledge_result = post_knowledge_search(query=knowledge_query)
            render_tool_invocation_result("Knowledge search", knowledge_result)
        except RuntimeError as exc:
            st.error(str(exc))

    with st.form("risk_score_account_form"):
        risk_query = st.text_area(
            "Risk Score Account Query",
            value="risk borrower account atlas score",
            height=100,
        )
        risk_submitted = st.form_submit_button(
            "Run Risk Score Account",
            use_container_width=True,
        )

    if risk_submitted:
        try:
            risk_result = post_risk_score_account(query=risk_query)
            render_tool_invocation_result("Risk score account", risk_result)
        except RuntimeError as exc:
            st.error(str(exc))

with tool_col2:
    with st.form("trade_query_metrics_form"):
        trade_query = st.text_area(
            "Trade Query Metrics Query",
            value="trade wallet volume gamma",
            height=100,
        )
        trade_submitted = st.form_submit_button(
            "Run Trade Query Metrics",
            use_container_width=True,
        )

    if trade_submitted:
        try:
            trade_result = post_trade_query_metrics(query=trade_query)
            render_tool_invocation_result("Trade query metrics", trade_result)
        except RuntimeError as exc:
            st.error(str(exc))

    with st.form("ops_create_alert_or_action_form"):
        ops_query = st.text_area(
            "Ops Create Alert Or Action Query",
            value="alert escalate suspicious risk review",
            height=100,
        )
        ops_submitted = st.form_submit_button(
            "Run Ops Create Alert Or Action",
            use_container_width=True,
        )

    if ops_submitted:
        try:
            ops_result = post_ops_create_alert_or_action(query=ops_query)
            render_tool_invocation_result("Ops create alert or action", ops_result)
        except RuntimeError as exc:
            st.error(str(exc))
