from frontend.services.retrieval import (
    parse_retrieval_citations,
    parse_retrieval_evidence,
)


def test_parse_retrieval_evidence_preserves_citations_chunks_and_metadata() -> None:
    evidence = parse_retrieval_evidence(
        {
            "query": "policy evidence",
            "retrieval_source": "postgresql_pgvector",
            "retrieved_chunks": [
                {
                    "document_id": "doc-1",
                    "title": "Trading Policy",
                    "summary": "Escalate suspicious activity.",
                    "chunk_id": "chunk-1",
                    "chunk_index": 2,
                    "source_path": "data/trading.md",
                    "score": 0.91,
                    "metadata": {"topic": "surveillance"},
                }
            ],
            "citations": [
                {
                    "document_id": "doc-1",
                    "title": "Trading Policy",
                    "chunk_id": "chunk-1",
                    "chunk_index": 2,
                    "source_path": "data/trading.md",
                    "score": 0.91,
                    "excerpt": "Escalate suspicious activity.",
                }
            ],
            "retrieval_metadata": {
                "provider": "local_sentence_transformer",
                "model_name": "sentence-transformers/all-MiniLM-L6-v2",
                "vector_dimensions": 384,
                "top_k": 5,
                "result_count": 1,
                "status": "completed",
            },
        }
    )

    assert evidence.query == "policy evidence"
    assert evidence.retrieval_source == "postgresql_pgvector"
    assert evidence.citations[0].excerpt == "Escalate suspicious activity."
    assert evidence.retrieved_chunks[0].metadata == {"topic": "surveillance"}
    assert evidence.metadata.model_name == "sentence-transformers/all-MiniLM-L6-v2"
    assert evidence.metadata.vector_dimensions == 384


def test_parse_retrieval_evidence_keeps_degraded_state_without_fake_citations() -> None:
    evidence = parse_retrieval_evidence(
        {
            "citations": [{"document_id": "missing-title"}, "invalid"],
            "retrieval_metadata": {
                "status": "failed",
                "failure_reason": "RuntimeError",
            },
        }
    )

    assert evidence.citations == []
    assert evidence.metadata.status == "failed"
    assert evidence.metadata.failure_reason == "RuntimeError"


def test_parse_retrieval_citations_ignores_malformed_items() -> None:
    citations = parse_retrieval_citations(
        [
            {"document_id": "doc-1", "title": "Valid"},
            {"document_id": "missing-title"},
            None,
        ]
    )

    assert len(citations) == 1
    assert citations[0].document_id == "doc-1"
