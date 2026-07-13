import streamlit as st

from frontend.components.auth import render_api_error, require_authenticated_session
from frontend.services.api import ApiError
from frontend.services.chat import post_chat_message
from frontend.services.risk import batch_score_accounts
from frontend.services.session import (
    get_active_chat_session_id,
    get_active_role,
    set_active_chat_session_id,
)


st.set_page_config(page_title="Risk Scoring", page_icon=":triangular_ruler:", layout="wide")
token, user = require_authenticated_session()

st.title("Risk Scoring")
st.caption(
    f"Batch scoring and alert drafting for {user.get('display_name', user.get('username', 'user'))}."
)

with st.form("risk_batch_score_form"):
    account_ids_text = st.text_area(
        "Account IDs",
        value="acct-atlas-01\nacct-beacon-17",
        help="Enter one account ID per line.",
        height=120,
    )
    score_submitted = st.form_submit_button("Run Batch Score", use_container_width=True)

if score_submitted:
    account_ids = [line.strip() for line in account_ids_text.splitlines() if line.strip()]
    if not account_ids:
        st.warning("Enter at least one account ID.")
    else:
        try:
            st.session_state["risk_batch_score"] = batch_score_accounts(
                account_ids,
                access_token=token,
            )
        except ApiError as exc:
            render_api_error(exc)

score_result = st.session_state.get("risk_batch_score")
if score_result:
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric("Total scored", str(score_result.get("total_scored", 0)))
    metric_col2.metric("Highest score", str(score_result.get("highest_risk_score", 0)))
    metric_col3.metric("Average score", str(score_result.get("average_risk_score", 0)))
    st.markdown("#### Profiles")
    st.dataframe(score_result.get("profiles", []), use_container_width=True)
    if score_result.get("missing_account_ids"):
        st.warning(f"Missing accounts: {score_result['missing_account_ids']}")

st.markdown("#### Draft an alert")
with st.form("risk_alert_draft_form"):
    alert_account_id = st.text_input("Account ID", value="acct-atlas-01")
    alert_prompt = st.text_area(
        "Alert instruction",
        value=(
            "Draft a risk alert for this account using the available evidence. "
            "Do not close or approve the alert."
        ),
        height=100,
    )
    alert_submitted = st.form_submit_button("Draft Alert", use_container_width=True)

if alert_submitted:
    try:
        response = post_chat_message(
            user_role=get_active_role(),
            message_text=f"Account {alert_account_id}: {alert_prompt}",
            session_id=get_active_chat_session_id(),
            access_token=token,
        )
        set_active_chat_session_id(response.session_id)
        st.write(response.reply_text)
        if response.actions:
            st.markdown("**Actions**")
            st.write(response.actions)
        if response.evidence:
            st.markdown("**Evidence**")
            st.write(response.evidence)
    except ApiError as exc:
        render_api_error(exc)
