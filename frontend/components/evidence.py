from urllib.parse import urlparse

import streamlit as st

from frontend.services.retrieval import RetrievalCitation, RetrievalEvidence


def render_citation_panel(
    citations: list[RetrievalCitation],
    title: str = "Knowledge Citations",
) -> None:
    if not citations:
        return

    st.markdown(f"#### {title}")
    st.caption(f"{len(citations)} source citation(s) returned by retrieval.")
    for index, citation in enumerate(citations, start=1):
        label = f"{index}. {citation.title}"
        if citation.chunk_index is not None:
            label += f" · chunk {citation.chunk_index}"
        with st.expander(label, expanded=index == 1):
            _render_citation_details(citation)


def render_retrieval_evidence(
    evidence: RetrievalEvidence,
    title: str = "Retrieved Evidence",
) -> None:
    status = evidence.metadata.status
    if status == "disabled":
        st.info("Knowledge retrieval is disabled; no citations were generated.")
    elif status == "unavailable":
        st.warning("Knowledge retrieval is unavailable; no citations were generated.")
    elif status == "failed":
        st.warning("Knowledge retrieval failed for this request; no citations were generated.")
    elif status == "empty":
        st.info("Knowledge retrieval completed but returned no matching chunks.")

    if evidence.retrieved_chunks:
        st.caption(f"Retrieved {len(evidence.retrieved_chunks)} knowledge chunk(s).")
        with st.expander("Retrieved chunk content", expanded=False):
            for chunk in evidence.retrieved_chunks:
                st.markdown(f"**{chunk.title}**")
                st.write(chunk.summary)

    render_citation_panel(evidence.citations, title=title)


def _render_citation_details(citation: RetrievalCitation) -> None:
    if citation.source_path:
        if _is_http_url(citation.source_path):
            st.link_button("Open source", citation.source_path)
        else:
            st.caption(f"Source reference: `{citation.source_path}`")
    if citation.chunk_id:
        st.caption(f"Chunk ID: `{citation.chunk_id}`")
    if citation.score is not None:
        st.caption(f"Similarity score: `{citation.score:.4f}`")
    if citation.excerpt:
        st.write(citation.excerpt)


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
