import streamlit as st


ROLE_OPTIONS = [
    "analyst",
    "risk_operator",
    "supervisor",
    "admin",
]

CHAT_SESSION_KEY = "active_chat_session_id"
AUTH_TOKEN_KEY = "auth_access_token"
AUTH_USER_KEY = "auth_user"
AUTH_ROLES_KEY = "auth_roles"


def get_active_role() -> str:
    return st.session_state.get("active_role", ROLE_OPTIONS[0])


def set_active_role(role: str) -> None:
    st.session_state["active_role"] = role


def get_active_chat_session_id() -> str | None:
    return st.session_state.get(CHAT_SESSION_KEY)


def set_active_chat_session_id(session_id: str | None) -> None:
    if session_id is None:
        st.session_state.pop(CHAT_SESSION_KEY, None)
        return
    st.session_state[CHAT_SESSION_KEY] = session_id


def get_auth_token() -> str | None:
    return st.session_state.get(AUTH_TOKEN_KEY)


def set_auth_token(token: str | None) -> None:
    if token is None:
        st.session_state.pop(AUTH_TOKEN_KEY, None)
        return
    st.session_state[AUTH_TOKEN_KEY] = token


def get_auth_user() -> dict[str, object] | None:
    return st.session_state.get(AUTH_USER_KEY)


def set_auth_identity(
    user: dict[str, object] | None,
    roles: list[str] | None = None,
) -> None:
    if user is None:
        st.session_state.pop(AUTH_USER_KEY, None)
        st.session_state.pop(AUTH_ROLES_KEY, None)
        return
    st.session_state[AUTH_USER_KEY] = user
    st.session_state[AUTH_ROLES_KEY] = list(roles or [])


def get_auth_roles() -> list[str]:
    return list(st.session_state.get(AUTH_ROLES_KEY, []))


def clear_auth_session() -> None:
    for key in (AUTH_TOKEN_KEY, AUTH_USER_KEY, AUTH_ROLES_KEY, CHAT_SESSION_KEY):
        st.session_state.pop(key, None)
