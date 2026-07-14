import streamlit as st

from frontend.services.api import ApiError, DEFAULT_API_BASE_URL
from frontend.services.health import get_health


def render_retrieval_runtime_status(
    api_base_url: str = DEFAULT_API_BASE_URL,
) -> None:
    """Render one shared, user-facing retrieval availability indicator."""

    try:
        retrieval = get_health(api_base_url=api_base_url).retrieval
    except ApiError:
        st.caption("Knowledge retrieval status is unavailable.")
        return

    if retrieval.state == "ready":
        st.caption(
            "Knowledge retrieval ready "
            f"({retrieval.provider or 'configured provider'}, "
            f"{retrieval.vector_dimensions or '?'} dimensions)."
        )
    elif retrieval.state == "disabled":
        st.warning("Knowledge retrieval is disabled by application configuration.")
    else:
        st.warning("Knowledge retrieval is currently unavailable.")
