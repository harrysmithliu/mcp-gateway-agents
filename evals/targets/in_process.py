from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from backend.agent.ports import ToolGatewayPort
from backend.agent.service import AgentService
from backend.mcp_gateway.registry import build_default_registry
from backend.retrieval.service import RetrievalService
from evals.contracts import EvalCase, EvalObservation


@dataclass(slots=True)
class InProcessEvaluationTarget:
    """Runs the deterministic rule-planner path without a model API call."""

    retrieval_service: RetrievalService
    registry: ToolGatewayPort | None = None

    def evaluate(self, case: EvalCase) -> EvalObservation:
        started_at = perf_counter()
        try:
            retrieval_service = self._resolve_retrieval_service(case)
            registry = self.registry or build_default_registry(
                retrieval_service=retrieval_service,
            )
            agent_service = AgentService(retrieval_service=retrieval_service)
            authorization_context = _build_authorization_context(case.role)
            sensitive_action_response = agent_service.build_sensitive_action_response(
                normalized_role=case.role,
                normalized_text=case.message_text,
            )
            if sensitive_action_response is not None:
                return _build_observation(
                    case=case,
                    tool_names=(),
                    invocation_results=(),
                    authorization_context=authorization_context,
                    latency_ms=_latency_ms(started_at),
                )

            tool_names, planned_tool_calls, evidence, actions = agent_service.plan_tool_calls(
                normalized_role=case.role,
                normalized_text=case.message_text,
                registry=registry,
            )
            invocation_results, invocation_evidence = agent_service.invoke_planned_tool_calls(
                normalized_role=case.role,
                normalized_text=case.message_text,
                planned_tool_calls=planned_tool_calls,
                registry=registry,
                authorization_context=authorization_context,
            )
            agent_service.build_agent_response(
                normalized_role=case.role,
                session_id=None,
                tool_names=tool_names,
                planned_tool_calls=planned_tool_calls,
                tool_invocation_results=invocation_results,
                evidence=[*evidence, *invocation_evidence],
                actions=actions,
            )
            return _build_observation(
                case=case,
                tool_names=tool_names,
                invocation_results=invocation_results,
                authorization_context=authorization_context,
                latency_ms=_latency_ms(started_at),
            )
        except Exception as exc:
            return EvalObservation(
                case_id=case.case_id,
                authorization_scope=tuple(
                    _build_authorization_context(case.role)["allowed_access_levels"]
                ),
                latency_ms=_latency_ms(started_at),
                error=type(exc).__name__,
            )

    def _resolve_retrieval_service(self, case: EvalCase) -> RetrievalService:
        if case.runtime_profile == "retrieval_disabled":
            return RetrievalService(enabled=False)
        return self.retrieval_service


def _build_authorization_context(role: str) -> dict[str, object]:
    if role == "admin":
        return {
            "access_level": "restricted",
            "allowed_access_levels": ["internal", "restricted"],
        }
    return {
        "access_level": "internal",
        "allowed_access_levels": ["internal"],
    }


def _build_observation(
    case: EvalCase,
    tool_names: tuple[str, ...] | list[str],
    invocation_results: tuple | list,
    authorization_context: dict[str, object],
    latency_ms: int,
) -> EvalObservation:
    citation_chunk_ids: list[str] = []
    retrieval_status: str | None = None
    citation_schema_valid = True
    invocation_statuses = []
    for result in invocation_results:
        invocation_statuses.append(result.invocation_status)
        if result.tool_name != "knowledge.search":
            continue
        payload = result.response_payload
        result_status = payload.get("result_status")
        if isinstance(result_status, str):
            retrieval_status = result_status
        metadata = payload.get("retrieval_metadata")
        if retrieval_status is None and isinstance(metadata, dict):
            status = metadata.get("status")
            retrieval_status = status if isinstance(status, str) else None
        raw_citations = payload.get("citations", [])
        if not isinstance(raw_citations, list):
            citation_schema_valid = False
            continue
        for citation in raw_citations:
            if not isinstance(citation, dict):
                citation_schema_valid = False
                continue
            if not all(
                isinstance(citation.get(field), str) and citation.get(field).strip()
                for field in ("document_id", "title", "chunk_id")
            ):
                citation_schema_valid = False
                continue
            citation_chunk_ids.append(citation["chunk_id"])
    return EvalObservation(
        case_id=case.case_id,
        tool_names=tuple(tool_names),
        invocation_statuses=tuple(invocation_statuses),
        citation_chunk_ids=tuple(dict.fromkeys(citation_chunk_ids)),
        retrieval_status=retrieval_status,
        authorization_scope=tuple(authorization_context["allowed_access_levels"]),
        citation_schema_valid=citation_schema_valid,
        latency_ms=latency_ms,
    )


def _latency_ms(started_at: float) -> int:
    return max(0, round((perf_counter() - started_at) * 1000))
