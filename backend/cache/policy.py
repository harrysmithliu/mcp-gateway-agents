from dataclasses import dataclass

from backend.cache.contracts import (
    CacheBypassReason,
    CacheDecision,
    CacheEligibility,
    CacheRequestContext,
)
from backend.cache.keys import DEFAULT_CACHE_KEY_PREFIX, build_cache_key


NON_CACHEABLE_RETRIEVAL_STATUSES = frozenset(
    {"empty", "disabled", "failed", "unavailable", "preview"}
)


@dataclass(frozen=True, slots=True)
class CacheEligibilityPolicy:
    """Pure policy for deciding whether a response may use the cache."""

    ttl_seconds: int = 300
    key_prefix: str = DEFAULT_CACHE_KEY_PREFIX

    def __post_init__(self) -> None:
        if self.ttl_seconds <= 0:
            raise ValueError("Cache TTL must be greater than zero.")
        if not self.key_prefix.strip():
            raise ValueError("Cache key prefix cannot be empty.")

    def evaluate(self, context: CacheRequestContext) -> CacheEligibility:
        """Return a typed decision without touching Redis or another provider."""

        reason = self._bypass_reason(context)
        if reason is not CacheBypassReason.NONE:
            return self._build_decision(
                context=context,
                decision=CacheDecision.BYPASS,
                reason=reason,
            )
        return self._build_decision(
            context=context,
            decision=CacheDecision.ELIGIBLE,
            reason=CacheBypassReason.NONE,
        )

    def _bypass_reason(
        self,
        context: CacheRequestContext,
    ) -> CacheBypassReason:
        if context.user_id is None:
            return CacheBypassReason.USER_ID_REQUIRED
        if not context.normalized_role.strip():
            return CacheBypassReason.ROLE_REQUIRED
        if not context.normalized_scope:
            return CacheBypassReason.AUTHORIZATION_SCOPE_REQUIRED
        if not context.session_id or not context.session_id.strip():
            return CacheBypassReason.SESSION_REQUIRED
        if not context.context_revision or not context.context_revision.strip():
            return CacheBypassReason.CONTEXT_REVISION_REQUIRED
        if not context.read_only:
            return CacheBypassReason.NOT_READ_ONLY
        if context.sensitive_action_requested:
            return CacheBypassReason.SENSITIVE_ACTION
        if context.guardrail_escalation_required:
            return CacheBypassReason.GUARDRAIL_ESCALATION
        if context.retrieval_status in NON_CACHEABLE_RETRIEVAL_STATUSES:
            return CacheBypassReason.RETRIEVAL_RESULT_NOT_CACHEABLE
        if not context.response_cacheable:
            return CacheBypassReason.RESPONSE_NOT_CACHEABLE
        return CacheBypassReason.NONE

    def _build_decision(
        self,
        context: CacheRequestContext,
        decision: CacheDecision,
        reason: CacheBypassReason,
    ) -> CacheEligibility:
        is_eligible = decision is CacheDecision.ELIGIBLE
        return CacheEligibility(
            decision=decision,
            reason=reason,
            cache_key=build_cache_key(context, self.key_prefix) if is_eligible else None,
            ttl_seconds=self.ttl_seconds if is_eligible else None,
        )
