import streamlit as st

from frontend.components.auth import require_authenticated_session


_, user = require_authenticated_session()


st.title("Dashboard")
st.caption("Authenticated entrypoint for investigation and operational review.")

st.write(f"Signed in as **{user.get('display_name', user.get('username', 'user'))}**.")
st.info("Use Account Investigation to search accounts and inspect risk, trading, and evidence context.")
st.info("Use the home page for chat and direct tool diagnostics.")
