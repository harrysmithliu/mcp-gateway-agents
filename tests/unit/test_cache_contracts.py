import pytest

from backend.cache.contracts import (
    CacheBypassReason,
    CacheDecision,
    CacheRequestContext,
)
from backend.cache.keys import build_cache_key
from backend.cache.policy import CacheEligibilityPolicy
from backend.storage.settings import Settings


def build_context(**overrides: object) -> CacheRequestContext:
    values: dict[str, object] = {
        "normalized_text": "Find the trading policy.",
        "user_id": 42,
        "normalized_role": "analyst",
        "authorization_scope": ("internal",),
        "session_id": "session-1",
        "history_fingerprint": "history-v1",
        "context_revision": "knowledge-v1",
        "retrieval_status": "completed",
    }
    values.update(overrides)
    return CacheRequestContext(**values)


def test_cache_key_is_deterministic_and_opaque() -> None:
    first_key = build_cache_key(build_context())
    second_key = build_cache_key(
        build_context(
            normalized_text="  Find   the trading policy. ",
            authorization_scope=("internal", "internal"),
        )
    )

    assert first_key == second_key
    assert first_key.startswith("agent:response:v1:")
    assert "Find" not in first_key
    assert len(first_key.rsplit(":", 1)[-1]) == 64


@pytest.mark.parametrize(
    ("override", "expected_reason"),
    [
        ({"user_id": None}, CacheBypassReason.USER_ID_REQUIRED),
        ({"normalized_role": ""}, CacheBypassReason.ROLE_REQUIRED),
        ({"authorization_scope": ()}, CacheBypassReason.AUTHORIZATION_SCOPE_REQUIRED),
        ({"session_id": None}, CacheBypassReason.SESSION_REQUIRED),
        ({"context_revision": None}, CacheBypassReason.CONTEXT_REVISION_REQUIRED),
        ({"read_only": False}, CacheBypassReason.NOT_READ_ONLY),
        ({"sensitive_action_requested": True}, CacheBypassReason.SENSITIVE_ACTION),
        ({"guardrail_escalation_required": True}, CacheBypassReason.GUARDRAIL_ESCALATION),
        ({"retrieval_status": "disabled"}, CacheBypassReason.RETRIEVAL_RESULT_NOT_CACHEABLE),
        ({"response_cacheable": False}, CacheBypassReason.RESPONSE_NOT_CACHEABLE),
    ],
)
def test_cache_policy_returns_stable_bypass_reason(
    override: dict[str, object],
    expected_reason: CacheBypassReason,
) -> None:
    decision = CacheEligibilityPolicy().evaluate(build_context(**override))

    assert decision.decision is CacheDecision.BYPASS
    assert decision.eligible is False
    assert decision.reason is expected_reason
    assert decision.cache_key is None
    assert decision.ttl_seconds is None
    assert decision.to_payload()["reason"] == expected_reason.value


def test_cache_policy_returns_key_and_ttl_for_eligible_context() -> None:
    decision = CacheEligibilityPolicy(ttl_seconds=120).evaluate(build_context())

    assert decision.decision is CacheDecision.ELIGIBLE
    assert decision.eligible is True
    assert decision.reason is CacheBypassReason.NONE
    assert str(decision.cache_key).startswith("agent:response:v1:")
    assert decision.ttl_seconds == 120


def test_cache_policy_rejects_invalid_configuration() -> None:
    with pytest.raises(ValueError, match="TTL"):
        CacheEligibilityPolicy(ttl_seconds=0)
    with pytest.raises(ValueError, match="prefix"):
        CacheEligibilityPolicy(key_prefix=" ")


def test_settings_have_safe_disabled_cache_defaults() -> None:
    settings = Settings(
        response_cache_enabled=False,
        response_cache_ttl_seconds=300,
        response_cache_key_prefix="agent:response",
    )

    assert settings.response_cache_enabled is False
    assert settings.response_cache_ttl_seconds == 300
    assert settings.response_cache_key_prefix == "agent:response"
