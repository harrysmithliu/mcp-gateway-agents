import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from frontend.services.chat import post_chat_message


def test_post_chat_message_parses_session_id(monkeypatch) -> None:
    def fake_post_json(
        endpoint_path: str,
        payload: dict[str, object],
        api_base_url: str = "http://localhost:8000",
        timeout_seconds: float = 5.0,
    ) -> dict[str, object]:
        _ = endpoint_path, payload, api_base_url, timeout_seconds
        return {
            "session_id": "session-frontend-001",
            "reply_text": "ok",
            "tool_names": ["knowledge.search"],
            "planned_tool_calls": [],
            "tool_invocation_results": [],
            "evidence": [],
            "actions": [],
            "citations": [
                {
                    "document_id": "doc-1",
                    "title": "Trading Policy",
                    "chunk_id": "chunk-1",
                    "chunk_index": 2,
                    "source_path": "data/trading.md",
                    "score": 0.91,
                    "excerpt": "Escalate suspicious activity.",
                }
            ],
            "planner_result": {
                "planner_source": "langchain_model",
                "retrieval_status": "completed",
                "retrieval_source": "postgresql_pgvector",
                "retrieval_result_count": 3,
                "grounded_chunk_count": 2,
                "grounding_truncated": True,
            },
        }

    monkeypatch.setattr("frontend.services.chat._post_json", fake_post_json)

    response = post_chat_message(
        user_role="analyst",
        message_text="hello",
    )

    assert response.session_id == "session-frontend-001"
    assert response.tool_names == ["knowledge.search"]
    assert response.citations[0].title == "Trading Policy"
    assert response.citations[0].chunk_index == 2
    assert response.citations[0].score == 0.91
    assert response.planner_result is not None
    assert response.planner_result.retrieval_status == "completed"
    assert response.planner_result.retrieval_source == "postgresql_pgvector"
    assert response.planner_result.retrieval_result_count == 3
    assert response.planner_result.grounded_chunk_count == 2
    assert response.planner_result.grounding_truncated is True
