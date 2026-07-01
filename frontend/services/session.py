import streamlit as st


ROLE_OPTIONS = [
    "viewer",
    "analyst",
    "risk_operator",
    "supervisor",
    "admin",
]


def get_active_role() -> str:
    return st.session_state.get("active_role", ROLE_OPTIONS[0])


def set_active_role(role: str) -> None:
    st.session_state["active_role"] = role

