import pytest
from pydantic import ValidationError

from backend.agent.planning.contracts import PlannerDecision
from backend.agent.planning.langchain import (
    StructuredPlannerUnavailableError,
    invoke_structured_planner,
)


class FakeStructuredModel:
    def __init__(self, response: object) -> None:
        self.response = response
        self.received_prompt: str | None = None

    def invoke(self, prompt: str) -> object:
        self.received_prompt = prompt
        return self.response


class FakePlannerModel:
    def __init__(self, response: object) -> None:
        self.structured_model = FakeStructuredModel(response)
        self.received_schema: type[PlannerDecision] | None = None

    def with_structured_output(
        self,
        schema: type[PlannerDecision],
    ) -> FakeStructuredModel:
        self.received_schema = schema
        return self.structured_model


def test_invoke_structured_planner_uses_planner_decision_schema() -> None:
    planner_model = FakePlannerModel(
        {"selected_tool_names": ["knowledge.search"]}
    )

    decision = invoke_structured_planner(planner_model, "planner prompt")

    assert planner_model.received_schema is PlannerDecision
    assert planner_model.structured_model.received_prompt == "planner prompt"
    assert decision == PlannerDecision(selected_tool_names=["knowledge.search"])


def test_invoke_structured_planner_accepts_typed_model_response() -> None:
    decision = PlannerDecision(selected_tool_names=["risk.score_account"])
    planner_model = FakePlannerModel(decision)

    assert invoke_structured_planner(planner_model, "planner prompt") is decision


def test_invoke_structured_planner_rejects_invalid_response() -> None:
    planner_model = FakePlannerModel({"selected_tool_names": "knowledge.search"})

    with pytest.raises(ValidationError):
        invoke_structured_planner(planner_model, "planner prompt")


def test_invoke_structured_planner_reports_unsupported_model() -> None:
    with pytest.raises(StructuredPlannerUnavailableError):
        invoke_structured_planner(object(), "planner prompt")
