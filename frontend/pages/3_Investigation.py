import streamlit as st

from frontend.components.auth import render_api_error, require_authenticated_session
from frontend.components.evidence import render_citation_panel
from frontend.components.retrieval import render_retrieval_runtime_status
from frontend.services.accounts import get_account_investigation, search_accounts
from frontend.services.api import ApiError
from frontend.services.chat import post_chat_message
from frontend.services.session import (
    get_active_chat_session_id,
    get_active_role,
    set_active_chat_session_id,
)


st.set_page_config(page_title="Investigation", page_icon=":mag:", layout="wide")
token, user = require_authenticated_session()

st.title("Account Investigation")
st.caption(
    f"Evidence workspace for {user.get('display_name', user.get('username', 'authenticated user'))}."
)
render_retrieval_runtime_status()

with st.form("account_search_form"):
    search_query = st.text_input(
        "Search accounts",
        value="high risk",
        help="Search by account label, jurisdiction, risk term, or anomaly keyword.",
    )
    search_submitted = st.form_submit_button("Search", use_container_width=True)

if search_submitted:
    try:
        st.session_state["investigation_search_results"] = search_accounts(
            query=search_query,
            access_token=token,
        )
    except ApiError as exc:
        render_api_error(exc)

search_results = st.session_state.get("investigation_search_results", {})
accounts = search_results.get("accounts", [])
if not accounts:
    st.info("Search for an account to begin an investigation.")
    st.stop()

account_by_id = {str(account["account_id"]): account for account in accounts}
selected_account_id = st.selectbox(
    "Account",
    list(account_by_id),
    format_func=lambda account_id: (
        f"{account_by_id[account_id]['account_label']} ({account_id})"
    ),
)

if st.button("Load Investigation", use_container_width=True):
    try:
        st.session_state["active_investigation"] = get_account_investigation(
            selected_account_id,
            access_token=token,
        )
    except ApiError as exc:
        render_api_error(exc)

investigation = st.session_state.get("active_investigation")
if not investigation:
    st.info("Select an account and load its investigation record.")
    st.stop()

overview = investigation["account_overview"]
risk_profile = investigation.get("risk_profile") or {}
trade_metrics = investigation.get("trade_metrics") or {}

metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
metric_col1.metric("Risk level", str(overview.get("risk_level", "unknown")))
metric_col2.metric("Risk score", str(risk_profile.get("risk_score", "n/a")))
metric_col3.metric("Exposure", f"${trade_metrics.get('net_exposure_usd', 0):,}")
metric_col4.metric("Review", str(overview.get("review_status", "unknown")))

st.subheader(str(overview.get("account_label", selected_account_id)))
st.json(
    {
        "account_id": overview.get("account_id"),
        "customer_id": overview.get("customer_id"),
        "account_type": overview.get("account_type"),
        "jurisdiction": overview.get("jurisdiction"),
        "anomaly_flags": overview.get("anomaly_flags", []),
    }
)

detail_col1, detail_col2 = st.columns(2)
with detail_col1:
    st.markdown("#### Risk profile")
    st.json(risk_profile)
with detail_col2:
    st.markdown("#### Trading metrics")
    st.json(trade_metrics)

st.markdown("#### Recent activity")
st.json(investigation.get("recent_activity") or {})

st.markdown("#### Draft finding with agent evidence")
with st.form("investigation_chat_form"):
    finding_prompt = st.text_area(
        "Question",
        value=(
            f"Summarize the evidence for account {selected_account_id} and recommend "
            "the next review step."
        ),
        height=100,
    )
    finding_submitted = st.form_submit_button("Draft Finding", use_container_width=True)

if finding_submitted:
    try:
        chat_response = post_chat_message(
            user_role=get_active_role(),
            message_text=finding_prompt,
            session_id=get_active_chat_session_id(),
            access_token=token,
        )
        set_active_chat_session_id(chat_response.session_id)
        st.write(chat_response.reply_text)
        if chat_response.evidence:
            st.markdown("**Evidence**")
            st.write(chat_response.evidence)
        if chat_response.actions:
            st.markdown("**Recommended actions**")
            st.write(chat_response.actions)
        render_citation_panel(chat_response.citations)
    except ApiError as exc:
        render_api_error(exc)
