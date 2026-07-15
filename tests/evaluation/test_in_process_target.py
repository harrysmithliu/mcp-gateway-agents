from dataclasses import dataclass

from backend.retrieval.contracts import (
    RetrievalCitation,
    RetrievalChunk,
    RetrievalContext,
    RetrievalMetadata,
    RetrievalQuery,
)
from evals.contracts import EvalCase
from evals.targets.in_process import InProcessEvaluationTarget


@dataclass(slots=True)
class FakeRetrievalService:
    def retrieve(self, query: RetrievalQuery) -> RetrievalContext:
        if "not present" in query.text:
            return RetrievalContext(
                rag_enabled=False,
                retrieval_source="postgresql_pgvector",
                metadata=RetrievalMetadata(
                    top_k=query.top_k,
                    status="empty",
                    result_count=0,
                ),
            )
        chunk_id = (
            "kb-risk-alert-handling-chunk-0"
            if "source path" in query.text
            else "kb-policy-trading-surveillance-chunk-0"
        )
        citation = RetrievalCitation(
            document_id="doc-1",
            title="Trading Policy",
            chunk_id=chunk_id,
            chunk_index=0,
            source_path="data/policy.md",
            score=0.91,
            excerpt="Policy evidence.",
        )
        return RetrievalContext(
            rag_enabled=True,
            retrieval_source="postgresql_pgvector",
            retrieved_chunks=[
                RetrievalChunk(
                    document_id="doc-1",
                    title="Trading Policy",
                    summary="Policy evidence.",
                    chunk_id=chunk_id,
                    chunk_index=0,
                    source_path="data/policy.md",
                    score=0.91,
                )
            ],
            citations=[citation],
            metadata=RetrievalMetadata(
                top_k=query.top_k,
                result_count=1,
                status="completed",
            ),
        )


def test_in_process_target_uses_rule_planner_and_captures_citations() -> None:
    observation = InProcessEvaluationTarget(
        retrieval_service=FakeRetrievalService(),
    ).evaluate(
        EvalCase(
            case_id="policy-case",
            role="analyst",
            message_text="Find the trading policy evidence.",
            required_tools=("knowledge.search",),
            expected_citation_chunk_ids=("kb-policy-trading-surveillance-chunk-0",),
            requires_rag=True,
        )
    )

    assert observation.tool_names == ("knowledge.search",)
    assert observation.invocation_statuses == ("completed",)
    assert observation.retrieval_status == "completed"
    assert observation.citation_chunk_ids == (
        "kb-policy-trading-surveillance-chunk-0",
    )
    assert observation.authorization_scope == ("internal",)
    assert observation.error is None


def test_in_process_target_derives_admin_scope_and_disabled_state() -> None:
    target = InProcessEvaluationTarget(retrieval_service=FakeRetrievalService())
    admin_observation = target.evaluate(
        EvalCase(
            case_id="admin-case",
            role="admin",
            message_text="Review the knowledge evidence and confirm the source path.",
            required_tools=("knowledge.search",),
        )
    )
    disabled_observation = target.evaluate(
        EvalCase(
            case_id="disabled-case",
            role="analyst",
            message_text="Find policy evidence while retrieval is disabled.",
            required_tools=("knowledge.search",),
            expected_invocation_status="unavailable",
            runtime_profile="retrieval_disabled",
        )
    )

    assert admin_observation.authorization_scope == ("internal", "restricted")
    assert disabled_observation.invocation_statuses == ("unavailable",)
    assert disabled_observation.retrieval_status == "disabled"
