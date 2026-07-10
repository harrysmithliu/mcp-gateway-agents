import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.api.app import app


def test_chat_route_returns_structured_response() -> None:
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={
            "user_role": "analyst",
            "message_text": "Please review trade risk and create an alert.",
        },
    )

    assert response.status_code == 200

    payload = response.json()
    assert set(payload) == {
        "session_id",
        "reply_text",
        "tool_names",
        "planned_tool_calls",
        "tool_invocation_results",
        "evidence",
        "actions",
        "citations",
        "planner_result",
    }
    assert isinstance(payload["session_id"], str)
    assert isinstance(payload["reply_text"], str)
    assert isinstance(payload["tool_names"], list)
    assert isinstance(payload["planned_tool_calls"], list)
    assert isinstance(payload["tool_invocation_results"], list)
    assert isinstance(payload["evidence"], list)
    assert isinstance(payload["actions"], list)
    assert isinstance(payload["citations"], list)
    assert isinstance(payload["planner_result"], dict)

    assert payload["planned_tool_calls"]
    first_planned_tool_call = payload["planned_tool_calls"][0]
    assert set(first_planned_tool_call) == {"tool_name", "domain", "description"}

    assert payload["tool_invocation_results"]
    first_tool_invocation_result = payload["tool_invocation_results"][0]
    assert set(first_tool_invocation_result) == {
        "tool_name",
        "domain",
        "invocation_status",
        "request_payload",
        "response_payload",
    }
    assert set(payload["planner_result"]) == {
        "planner_source",
        "raw_output_text",
        "candidate_tool_names",
        "selected_tool_names",
        "used_fallback",
        "fallback_reason",
    }


def test_chat_route_returns_multiple_tool_invocation_results() -> None:
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={
            "user_role": "analyst",
            "message_text": (
                "Please search the policy playbook, score this borrower account, "
                "query wallet order volume, and create an alert for review."
            ),
        },
    )

    assert response.status_code == 200

    payload = response.json()
    assert payload["session_id"] is not None
    expected_tool_names = [
        "knowledge.search",
        "risk.score_account",
        "trade.query_metrics",
        "ops.create_alert_or_action",
    ]

    assert payload["tool_names"] == expected_tool_names
    assert [item["tool_name"] for item in payload["planned_tool_calls"]] == expected_tool_names
    assert [item["tool_name"] for item in payload["tool_invocation_results"]] == expected_tool_names
    assert all(
        item["invocation_status"] == "completed"
        for item in payload["tool_invocation_results"]
    )
