import streamlit as st

from frontend.components.auth import render_api_error, require_authenticated_session
from frontend.services.api import ApiError
from frontend.services.ops import (
    decide_approval,
    list_alerts,
    list_approvals,
    request_approval,
    update_alert_status,
)
from frontend.services.session import get_auth_roles


st.set_page_config(page_title="Alerts", page_icon=":bell:", layout="wide")
token, user = require_authenticated_session()
roles = get_auth_roles()

st.title("Alerts and Approvals")
st.caption(
    f"Operational review for {user.get('display_name', user.get('username', 'user'))}."
)

if st.button("Refresh Alerts", use_container_width=True):
    st.rerun()

try:
    alerts_payload = list_alerts(access_token=token)
    approvals_payload = list_approvals(access_token=token)
except ApiError as exc:
    render_api_error(exc)
    st.stop()

st.markdown("#### Recent alerts")
alerts = alerts_payload.get("alerts", [])
st.dataframe(alerts, use_container_width=True)

if alerts:
    alert_ids = [str(alert["alert_id"]) for alert in alerts]
    selected_alert_id = st.selectbox("Alert", alert_ids)
    selected_alert = next(
        alert for alert in alerts if str(alert["alert_id"]) == selected_alert_id
    )
    st.json(selected_alert)

    if "risk_operator" in roles:
        with st.form("acknowledge_alert_form"):
            acknowledge_submitted = st.form_submit_button(
                "Acknowledge Alert",
                use_container_width=True,
            )
        if acknowledge_submitted:
            try:
                st.json(
                    update_alert_status(
                        selected_alert_id,
                        "acknowledged",
                        access_token=token,
                    )
                )
            except ApiError as exc:
                render_api_error(exc)

    with st.form("request_approval_form"):
        approval_reason = st.text_input(
            "Approval reason",
            value="Sensitive action requires supervisor review.",
        )
        approval_submitted = st.form_submit_button(
            "Request Approval",
            use_container_width=True,
        )
    if approval_submitted:
        try:
            st.json(
                request_approval(
                    selected_alert_id,
                    approval_reason,
                    access_token=token,
                )
            )
        except ApiError as exc:
            render_api_error(exc)

st.markdown("#### Approval queue")
approvals = approvals_payload.get("approvals", [])
st.dataframe(approvals, use_container_width=True)

if approvals and ("supervisor" in roles or "admin" in roles):
    requested_approvals = [
        approval
        for approval in approvals
        if approval.get("approval_status") == "requested"
    ]
    if requested_approvals:
        approval_by_id = {
            str(approval["approval_id"]): approval for approval in requested_approvals
        }
        selected_approval_id = st.selectbox(
            "Pending approval",
            list(approval_by_id),
        )
        with st.form("decide_approval_form"):
            decision = st.selectbox("Decision", ["approved", "rejected"])
            decision_reason = st.text_input(
                "Decision reason",
                value="Reviewed evidence and operational context.",
            )
            decision_submitted = st.form_submit_button(
                "Record Decision",
                use_container_width=True,
            )
        if decision_submitted:
            try:
                st.json(
                    decide_approval(
                        selected_approval_id,
                        decision,
                        decision_reason,
                        access_token=token,
                    )
                )
            except ApiError as exc:
                render_api_error(exc)
