from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.smoke.http_helpers import assert_success, build_demo_client


def test_chat_preserves_session_and_runtime_telemetry_across_turns() -> None:
    client = build_demo_client("analyst_demo")

    first_payload = assert_success(
        client.post(
            "/chat",
            json={
                "user_role": "analyst",
                "message_text": "Search the policy playbook for monitoring guidance.",
            },
        )
    )
    session_id = first_payload["session_id"]
    assert isinstance(session_id, str)
    assert session_id

    second_payload = assert_success(
        client.post(
            "/chat",
            json={
                "user_role": "analyst",
                "session_id": session_id,
                "message_text": "What should I monitor next in the same case?",
            },
        )
    )

    assert second_payload["session_id"] == session_id
    assert second_payload["cache_status"] in {"disabled", "hit", "miss", "bypassed"}
    assert second_payload["planner_result"]["history_source"] in {
        "current_turn_only",
        "persisted",
        "redis",
        "request_payload",
    }
    assert second_payload["evidence_guardrail_status"] in {
        "not_applicable",
        "no_grounding",
        "downgraded",
        "grounded",
    }
