import pytest
from pydantic import ValidationError

from backend.agent.planning.contracts import PlannerDecision


def test_planner_decision_accepts_multiple_selected_tools() -> None:
    decision = PlannerDecision(
        selected_tool_names=["knowledge.search", "risk.score_account"]
    )

    assert decision.contract_version == "planner.v1"
    assert decision.selected_tool_names == [
        "knowledge.search",
        "risk.score_account",
    ]


def test_planner_decision_allows_empty_selection_for_fallback_classification() -> None:
    decision = PlannerDecision()

    assert decision.selected_tool_names == []


def test_planner_decision_rejects_unexpected_fields() -> None:
    with pytest.raises(ValidationError):
        PlannerDecision.model_validate(
            {
                "selected_tool_names": ["knowledge.search"],
                "unexpected": "not part of planner contract",
            }
        )
