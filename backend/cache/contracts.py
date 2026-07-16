from dataclasses import dataclass, field
from enum import StrEnum
from time import time
from typing import Mapping


CACHE_CONTRACT_VERSION = "agent.response-cache/v1"


class CacheDecision(StrEnum):
    """High-level outcome of evaluating a response-cache candidate."""

    ELIGIBLE = "eligible"
    BYPASS = "bypass"


class CacheBypassReason(StrEnum):
    """Stable reasons explaining why a response must not enter the cache."""

    NONE = "none"
    USER_ID_REQUIRED = "user_id_required"
    ROLE_REQUIRED = "role_required"
    AUTHORIZATION_SCOPE_REQUIRED = "authorization_scope_required"
    SESSION_REQUIRED = "session_required"
    CONTEXT_REVISION_REQUIRED = "context_revision_required"
    NOT_READ_ONLY = "not_read_only"
    SENSITIVE_ACTION = "sensitive_action"
    GUARDRAIL_ESCALATION = "guardrail_escalation"
    RETRIEVAL_RESULT_NOT_CACHEABLE = "retrieval_result_not_cacheable"
    RESPONSE_NOT_CACHEABLE = "response_not_cacheable"


@dataclass(frozen=True, slots=True)
class CacheEligibility:
    """Typed cache decision shared by policy, orchestration and telemetry."""

    decision: CacheDecision
    reason: CacheBypassReason
    cache_key: str | None = None
    ttl_seconds: int | None = None

    @property
    def eligible(self) -> bool:
        return self.decision is CacheDecision.ELIGIBLE

    def to_payload(self) -> dict[str, object]:
        return {
            "decision": self.decision.value,
            "reason": self.reason.value,
            "eligible": self.eligible,
            "cache_key": self.cache_key,
            "ttl_seconds": self.ttl_seconds,
        }


@dataclass(frozen=True, slots=True)
class CacheRequestContext:
    """Identity and execution context used to isolate one cache candidate."""

    normalized_text: str
    user_id: int | None
    normalized_role: str
    authorization_scope: tuple[str, ...] = ()
    session_id: str | None = None
    history_fingerprint: str = ""
    context_revision: str | None = None
    response_contract_version: str = "agent.response/v1"
    read_only: bool = True
    sensitive_action_requested: bool = False
    guardrail_escalation_required: bool = False
    retrieval_status: str | None = None
    response_cacheable: bool = True

    @property
    def normalized_scope(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    value.strip().lower()
                    for value in self.authorization_scope
                    if value.strip()
                }
            )
        )


@dataclass(frozen=True, slots=True)
class CacheEntry:
    """Serialized response envelope accepted by a response-cache adapter."""

    cache_key: str
    response_payload: Mapping[str, object]
    ttl_seconds: int
    created_at_epoch: float = field(default_factory=time)

    def to_payload(self) -> dict[str, object]:
        return {
            "cache_key": self.cache_key,
            "response_payload": dict(self.response_payload),
            "ttl_seconds": self.ttl_seconds,
            "created_at_epoch": self.created_at_epoch,
        }
