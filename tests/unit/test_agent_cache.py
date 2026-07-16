from backend.agent.models import ChatCommand
from backend.agent.service import AgentService
from backend.cache.contracts import CacheReadResult, CacheStatus, CacheWriteResult
from backend.cache.policy import CacheEligibilityPolicy
from backend.mcp_gateway.models import ToolInvocationResult
from backend.mcp_gateway.registry import build_default_registry


class FakeResponseCache:
    def __init__(self) -> None:
        self.entries = {}
        self.get_calls = 0
        self.set_calls = 0

    def get(self, cache_key: str) -> CacheReadResult:
        self.get_calls += 1
        entry = self.entries.get(cache_key)
        if entry is None:
            return CacheReadResult(status=CacheStatus.MISS)
        return CacheReadResult(status=CacheStatus.HIT, entry=entry)

    def set(self, entry) -> CacheWriteResult:
        self.set_calls += 1
        self.entries[entry.cache_key] = entry
        return CacheWriteResult(status=CacheStatus.STORED)

    def delete(self, cache_key: str) -> bool:
        return self.entries.pop(cache_key, None) is not None


class CountingRegistry:
    def __init__(self) -> None:
        self.registry = build_default_registry()
        self.invoke_count = 0

    def get_tool(self, tool_name: str):
        return self.registry.get_tool(tool_name)

    def list_tool_names(self) -> list[str]:
        return self.registry.list_tool_names()

    def invoke(self, tool_name: str, request_payload=None) -> ToolInvocationResult:
        self.invoke_count += 1
        return self.registry.invoke(tool_name, request_payload)


def build_cache_enabled_service(cache: FakeResponseCache) -> AgentService:
    return AgentService(
        planner_override_output="trade.query_metrics",
        response_cache=cache,
        cache_policy=CacheEligibilityPolicy(ttl_seconds=120),
        response_cache_enabled=True,
    )


def build_cacheable_command(message_text: str) -> ChatCommand:
    return ChatCommand(
        user_role="analyst",
        message_text=message_text,
        session_id="cache-session",
        user_id=42,
        authorization_context={"allowed_access_levels": ["internal"]},
    )


def test_agent_service_stores_then_hits_read_only_response() -> None:
    cache = FakeResponseCache()
    registry = CountingRegistry()
    service = build_cache_enabled_service(cache)
    command = build_cacheable_command("Query the trade volume for Gamma.")

    first_response = service.handle_command(command, registry=registry)
    second_response = service.handle_command(command, registry=registry)

    assert first_response.cache_status == "miss"
    assert second_response.cache_status == "hit"
    assert second_response.reply_text == first_response.reply_text
    assert second_response.tool_names == ["trade.query_metrics"]
    assert registry.invoke_count == 1
    assert cache.get_calls == 2
    assert cache.set_calls == 1


def test_agent_service_bypasses_cache_for_operations_request() -> None:
    cache = FakeResponseCache()
    service = build_cache_enabled_service(cache)
    command = build_cacheable_command("Create an alert for this trade review.")

    response = service.handle_command(command, registry=CountingRegistry())

    assert response.cache_status == "bypass"
    assert response.cache_reason == "not_read_only"
    assert cache.get_calls == 0
    assert cache.set_calls == 0


def test_agent_service_keeps_cache_disabled_without_explicit_enablement() -> None:
    cache = FakeResponseCache()
    service = AgentService(response_cache=cache, cache_policy=CacheEligibilityPolicy())

    response = service.handle_command(
        build_cacheable_command("Query the trade volume for Gamma."),
        registry=CountingRegistry(),
    )

    assert response.cache_status == "disabled"
    assert response.cache_reason is None
    assert cache.get_calls == 0
    assert cache.set_calls == 0
