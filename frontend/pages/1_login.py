import streamlit as st

from frontend.services.session import ROLE_OPTIONS, get_active_role, set_active_role


st.title("Login / Role Switch")
st.caption("Demo entry for RBAC-aware flows.")

selected_role = st.radio("Select a demo role", ROLE_OPTIONS, index=ROLE_OPTIONS.index(get_active_role()))

if st.button("Activate Role", use_container_width=True):
    set_active_role(selected_role)
    st.success(f"Role activated: {selected_role}")

st.write(
    "A full authentication flow can replace this page later without changing the main "
    "application structure."
)
