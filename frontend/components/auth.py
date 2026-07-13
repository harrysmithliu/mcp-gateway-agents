import streamlit as st

from frontend.services.api import ApiError
from frontend.services.session import get_auth_token, get_auth_user


def require_authenticated_session() -> tuple[str, dict[str, object]]:
    token = get_auth_token()
    user = get_auth_user()
    if token is None or user is None:
        st.warning("Sign in from the Home page before opening this workspace.")
        st.stop()
    return token, user


def render_api_error(error: ApiError) -> None:
    if error.status_code in {401, 403}:
        st.error(f"Access denied ({error.status_code}). Sign in again or use an allowed role.")
        return
    st.error(str(error))
