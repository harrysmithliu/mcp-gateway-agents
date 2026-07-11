import logging

from backend.agent.service import AgentService
from backend.mcp_gateway.registry import build_default_registry


class StructuredModel:
    def __init__(self, response: object) -> None:
        self.response = response

    def with_structured_output(self, _schema):
        return self

    def invoke(self, _prompt: str) -> object:
        return self.response


def build_planner_result(monkeypatch, response: object):
    monkeypatch.setattr(
        AgentService,
        "init_langchain_chat_model",
        lambda self: StructuredModel(response),
    )
    return AgentService().build_langchain_planner_result(
        normalized_role="analyst",
        normalized_text="Search policy evidence.",
        registry=build_default_registry(),
    )


def test_structured_planner_success_returns_canonical_tool_names(monkeypatch) -> None:
    result = build_planner_result(
        monkeypatch,
        {"selected_tool_names": ["KNOWLEDGE.SEARCH"]},
    )

    assert result.planner_source == "langchain_model"
    assert result.planner_mode == "structured"
    assert result.model_provider == "anthropic"
    assert result.model_name == "claude-haiku-4-5"
    assert result.latency_ms >= 0
    assert result.selected_tool_names == ["knowledge.search"]
    assert result.used_fallback is False


def test_structured_planner_empty_selection_uses_rule_fallback(monkeypatch) -> None:
    result = build_planner_result(monkeypatch, {"selected_tool_names": []})

    assert result.used_fallback is True
    assert result.planner_mode == "rule_fallback"
    assert result.latency_ms >= 0
    assert result.fallback_reason == "empty_selection"
    assert result.selected_tool_names == ["knowledge.search"]


def test_structured_planner_unknown_tool_uses_rule_fallback(monkeypatch) -> None:
    result = build_planner_result(
        monkeypatch,
        {"selected_tool_names": ["unknown.tool"]},
    )

    assert result.used_fallback is True
    assert result.planner_mode == "rule_fallback"
    assert result.fallback_reason == "invalid_tool_selection"


def test_structured_planner_schema_failure_uses_rule_fallback(monkeypatch) -> None:
    result = build_planner_result(
        monkeypatch,
        {"selected_tool_names": "knowledge.search"},
    )

    assert result.used_fallback is True
    assert result.planner_mode == "rule_fallback"
    assert result.fallback_reason == "schema_validation_failed"


def test_planner_telemetry_log_contains_status_only(caplog) -> None:
    caplog.set_level(logging.INFO, logger="backend.agent.service")
    service = AgentService(planner_override_output="knowledge.search")

    service.plan_tool_calls_with_langchain(
        normalized_role="analyst",
        normalized_text="Review secret policy details.",
        registry=build_default_registry(),
    )

    planner_records = [
        record
        for record in caplog.records
        if record.message == "Planner execution completed"
    ]
    assert len(planner_records) == 1
    record = planner_records[0]
    assert record.planner_source == "planner_override"
    assert record.planner_mode == "override"
    assert record.selected_tool_count == 1
    assert "secret policy details" not in caplog.text
