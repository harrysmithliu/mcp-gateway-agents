from __future__ import annotations

from backend.verification.contracts import VerificationStage


STAGE_CATALOG: dict[str, VerificationStage] = {
    "readiness": VerificationStage(
        name="readiness",
        description="Check backend, frontend, PostgreSQL, Redis, retrieval, cache, and MCP readiness.",
        script_path="scripts/doctor_local_runtime.py",
        arguments=("--require-frontend",),
        requires_runtime=True,
    ),
    "data_state": VerificationStage(
        name="data_state",
        description="Verify repeatable knowledge refresh, persisted vectors, and evidence integrity.",
        script_path="scripts/verify_round8_evidence_layer.py",
        depends_on=("readiness",),
        requires_runtime=True,
        mutates_local_state=True,
    ),
    "rag_mcp": VerificationStage(
        name="rag_mcp",
        description="Verify retrieval access scopes, citations, disabled behavior, and MCP parity.",
        script_path="scripts/verify_round6_mcp_retrieval.py",
        depends_on=("readiness", "data_state"),
        requires_runtime=True,
    ),
    "workflow": VerificationStage(
        name="workflow",
        description="Verify authenticated analyst, risk operator, supervisor, and audit workflows.",
        script_path="scripts/verify_round7_workflow.py",
        depends_on=("readiness",),
        requires_runtime=True,
        mutates_local_state=True,
    ),
    "cache_guardrails": VerificationStage(
        name="cache_guardrails",
        description="Verify cache fallback, bounded memory, evidence guardrails, and action blocking.",
        script_path="scripts/verify_batch6_closure.py",
    ),
    "evaluation": VerificationStage(
        name="evaluation",
        description="Run the deterministic core_v1 agent evaluation dataset.",
        script_path="scripts/run_agent_evaluation.py",
        requires_runtime=True,
    ),
    "anthropic_planner": VerificationStage(
        name="anthropic_planner",
        description="Run one explicit live Anthropic structured-planner smoke request.",
        script_path="scripts/verify_anthropic_planner.py",
        paid_provider=True,
    ),
}


PROFILES: dict[str, tuple[str, ...]] = {
    "offline": ("cache_guardrails",),
    "local": (
        "readiness",
        "data_state",
        "rag_mcp",
        "workflow",
        "cache_guardrails",
        "evaluation",
    ),
}


def list_stage_names(include_paid_provider: bool = False) -> tuple[str, ...]:
    return tuple(
        name
        for name, stage in STAGE_CATALOG.items()
        if include_paid_provider or not stage.paid_provider
    )


def resolve_stage_selection(
    stage_names: tuple[str, ...],
    *,
    profile: str | None = None,
    allow_paid_provider: bool = False,
) -> tuple[str, ...]:
    requested = PROFILES[profile] if profile is not None else stage_names
    expanded: list[str] = []
    visiting: set[str] = set()

    def visit(stage_name: str) -> None:
        if stage_name in visiting:
            raise ValueError(f"Verification stage dependency cycle: {stage_name}")
        if stage_name not in STAGE_CATALOG:
            raise ValueError(f"Unknown verification stage: {stage_name}")
        stage = STAGE_CATALOG[stage_name]
        if stage.paid_provider and not allow_paid_provider:
            raise ValueError(
                "Paid-provider stage requires explicit --allow-paid-provider."
            )
        if stage_name in expanded:
            return
        visiting.add(stage_name)
        for dependency in stage.depends_on:
            visit(dependency)
        visiting.remove(stage_name)
        expanded.append(stage_name)

    for stage_name in requested:
        visit(stage_name)
    return tuple(expanded)
