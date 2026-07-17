from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.smoke.http_helpers import assert_success, build_demo_client


def test_analyst_chat_exposes_evidence_contract() -> None:
    client = build_demo_client("analyst_demo")

    payload = assert_success(
        client.post(
            "/chat",
            json={
                "user_role": "analyst",
                "message_text": "Search the policy playbook for account review guidance.",
            },
        )
    )

    assert "knowledge.search" in payload["tool_names"]
    assert isinstance(payload["citations"], list)
    assert payload["planner_result"]["retrieval_status"] in {
        "disabled",
        "empty",
        "completed",
        "degraded",
    }
    assert payload["evidence_guardrail_status"] in {
        "not_applicable",
        "no_grounding",
        "downgraded",
        "grounded",
    }


def test_analyst_knowledge_scope_is_server_owned() -> None:
    client = build_demo_client("analyst_demo")

    payload = assert_success(
        client.post(
            "/tools/knowledge-search",
            json={
                "query": "restricted policy evidence",
                "access_level": "restricted",
            },
        )
    )

    request_payload = payload["request_payload"]
    assert "access_level" not in request_payload
    assert request_payload["authorization_context"]["allowed_access_levels"] == [
        "internal"
    ]
    assert payload["response_payload"]["contract_version"] == "knowledge.search/v1"
    assert isinstance(payload["response_payload"]["citations"], list)
