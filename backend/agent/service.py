from dataclasses import dataclass


@dataclass(slots=True)
class AgentService:
    """Phase 1 placeholder for future agent orchestration."""

    provider_name: str = "anthropic"

    def describe(self) -> str:
        return (
            "Phase 1 placeholder agent service. "
            "Tool routing, cache, RAG, and guardrails will be added in later phases."
        )

