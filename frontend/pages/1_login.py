import streamlit as st

from frontend.services.session import ROLE_OPTIONS, get_active_role, set_active_role


st.title("Role Context")
st.caption("Authentication is handled from the Home page sidebar.")

selected_role = st.radio("Select a demo role", ROLE_OPTIONS, index=ROLE_OPTIONS.index(get_active_role()))

if st.button("Activate Role", use_container_width=True):
    set_active_role(selected_role)
    st.success(f"Role activated: {selected_role}")

st.write("Use this page to preview an available role context for RBAC-aware flows.")
