import streamlit as st

from frontend.components.auth import render_api_error, require_authenticated_session
from frontend.services.api import ApiError
from frontend.services.knowledge_ingestion import (
    list_knowledge_ingestion_runs,
    trigger_knowledge_ingestion,
)
from frontend.services.session import get_auth_roles


st.set_page_config(page_title="Knowledge Administration", page_icon=":books:", layout="wide")
token, user = require_authenticated_session()

if "admin" not in get_auth_roles():
    st.error("Knowledge administration requires the admin role.")
    st.stop()

st.title("Knowledge Administration")
st.caption(
    f"Controlled local knowledge refresh for {user.get('display_name', user.get('username', 'admin'))}."
)

if st.button("Run Manual Refresh", type="primary", use_container_width=True):
    try:
        st.session_state["knowledge_ingestion_last_run"] = trigger_knowledge_ingestion(
            access_token=token,
        )
        run_status = st.session_state["knowledge_ingestion_last_run"].get("run", {}).get(
            "status"
        )
        if run_status == "succeeded":
            st.success("Knowledge ingestion run completed.")
        else:
            st.warning(f"Knowledge ingestion run ended with status: {run_status}.")
    except ApiError as exc:
        render_api_error(exc)

try:
    runs_payload = list_knowledge_ingestion_runs(access_token=token)
except ApiError as exc:
    render_api_error(exc)
    runs_payload = {"query_status": "degraded", "runs": []}

st.caption(f"Query status: `{runs_payload.get('query_status', 'unknown')}`")
runs = runs_payload.get("runs", [])
if runs:
    st.dataframe(runs, use_container_width=True)
else:
    st.info("No ingestion runs have been recorded yet.")

last_run = st.session_state.get("knowledge_ingestion_last_run")
if last_run:
    st.markdown("#### Latest run")
    run = last_run.get("run", {})
    sources = last_run.get("sources", [])
    st.write(
        {
            "run_id": run.get("run_id"),
            "status": run.get("status"),
            "source_count": run.get("source_count"),
            "document_count": run.get("document_count"),
            "chunk_count": run.get("chunk_count"),
            "embedding_count": run.get("embedding_count"),
            "embedding_model_name": run.get("embedding_model_name"),
            "change_summary": run.get("change_summary", {}),
            "error_summary": run.get("error_summary"),
        }
    )
    change_summary = run.get("change_summary", {})
    if change_summary:
        st.markdown("#### Refresh summary")
        st.dataframe(
            [
                {
                    "new": change_summary.get("new_source_count", 0),
                    "changed": change_summary.get("changed_source_count", 0),
                    "unchanged": change_summary.get("unchanged_source_count", 0),
                    "removed": change_summary.get("removed_source_count", 0),
                    "reindexed": change_summary.get("reindexed_source_count", 0),
                    "no_op": change_summary.get("no_op", False),
                }
            ],
            use_container_width=True,
            hide_index=True,
        )
    if sources:
        st.markdown("#### Source manifest")
        st.dataframe(sources, use_container_width=True)
