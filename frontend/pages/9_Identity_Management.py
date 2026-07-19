import streamlit as st

from frontend.components.auth import render_api_error, require_authenticated_session
from frontend.services.admin_management import (
    create_admin_user,
    list_admin_users,
    list_runtime_switches,
    replace_admin_user_roles,
    set_admin_user_activity,
    set_runtime_switch,
)
from frontend.services.api import ApiError
from frontend.services.session import get_auth_roles


ROLE_OPTIONS = ["analyst", "risk_operator", "supervisor", "admin"]


st.set_page_config(page_title="Identity Management", page_icon=":busts_in_silhouette:", layout="wide")
token, user = require_authenticated_session()

if "admin" not in get_auth_roles():
    st.error("Identity management requires the admin role.")
    st.stop()

st.title("Identity Management")
st.caption(
    f"Manage local users, roles, and safe runtime controls for "
    f"{user.get('display_name', user.get('username', 'admin'))}."
)

try:
    users = list_admin_users(access_token=token)
    switches = list_runtime_switches(access_token=token)
except ApiError as exc:
    render_api_error(exc)
    st.stop()

st.markdown("#### Create user")
with st.form("create-admin-user", clear_on_submit=True):
    create_left, create_right = st.columns(2)
    with create_left:
        username = st.text_input("Username")
        display_name = st.text_input("Display name")
    with create_right:
        password = st.text_input("Initial password", type="password")
        selected_roles = st.multiselect("Roles", ROLE_OPTIONS, default=["analyst"])
    create_submitted = st.form_submit_button("Create user", type="primary")

if create_submitted:
    try:
        create_admin_user(
            username=username,
            display_name=display_name,
            password=password,
            roles=selected_roles,
            access_token=token,
        )
        st.success("User created. Refresh the page to view the current directory.")
    except ApiError as exc:
        render_api_error(exc)

st.markdown("#### User directory")
if users:
    st.dataframe(users, use_container_width=True, hide_index=True)
    user_options = {f"{item['username']} ({item['user_id']})": item for item in users}
    selected_label = st.selectbox("Select a user to manage", user_options)
    selected_user = user_options[selected_label]
    current_roles = [str(role) for role in selected_user.get("roles", [])]

    roles_column, activity_column = st.columns(2)
    with roles_column:
        with st.form("replace-admin-user-roles"):
            updated_roles = st.multiselect(
                "Assigned roles",
                ROLE_OPTIONS,
                default=current_roles,
            )
            replace_roles_submitted = st.form_submit_button("Replace roles")
        if replace_roles_submitted:
            try:
                replace_admin_user_roles(
                    user_id=int(selected_user["user_id"]),
                    roles=updated_roles,
                    access_token=token,
                )
                st.success("Roles updated. Existing sessions for this user were revoked.")
            except ApiError as exc:
                render_api_error(exc)
    with activity_column:
        target_activity = st.toggle(
            "User is active",
            value=bool(selected_user.get("is_active", False)),
        )
        if st.button("Save active status", use_container_width=True):
            try:
                set_admin_user_activity(
                    user_id=int(selected_user["user_id"]),
                    is_active=target_activity,
                    access_token=token,
                )
                st.success("User activity updated.")
            except ApiError as exc:
                render_api_error(exc)
else:
    st.info("No users were returned by the identity service.")

st.markdown("#### Runtime switches")
for switch in switches:
    switch_key = str(switch["key"])
    switch_column, action_column = st.columns([4, 1])
    with switch_column:
        target_enabled = st.toggle(
            f"{switch_key}: {switch.get('description', '')}",
            value=bool(switch.get("is_enabled", False)),
            key=f"runtime-switch-{switch_key}",
        )
    with action_column:
        st.write("")
        if st.button("Apply", key=f"apply-runtime-switch-{switch_key}"):
            try:
                set_runtime_switch(
                    key=switch_key,
                    is_enabled=target_enabled,
                    access_token=token,
                )
                st.success(f"{switch_key} updated.")
            except ApiError as exc:
                render_api_error(exc)
