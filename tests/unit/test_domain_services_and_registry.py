import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.mcp_gateway.registry import build_default_registry
from backend.services.knowledge import KnowledgeService
from backend.services.operations import OperationsService
from backend.services.risk import RiskService
from backend.services.trade import TradeService


def test_knowledge_service_search_returns_ranked_matches() -> None:
    knowledge_service = KnowledgeService()

    response_payload = knowledge_service.search(
        query_text="policy evidence suspicious trade exposure",
        limit=3,
    )

    assert response_payload["query"] == "policy evidence suspicious trade exposure"
    assert response_payload["total_matches"] >= 1
    assert response_payload["matches"][0]["match_score"] >= 1


def test_trade_service_query_metrics_returns_aggregated_metrics() -> None:
    trade_service = TradeService()

    response_payload = trade_service.query_metrics(
        query_text="trade wallet volume gamma",
        limit=3,
    )

    assert response_payload["query"] == "trade wallet volume gamma"
    assert response_payload["total_matches"] >= 1
    assert response_payload["total_filled_notional_usd_24h"] >= 0
    assert response_payload["snapshots"]


def test_risk_service_score_account_returns_ranked_profiles() -> None:
    risk_service = RiskService()

    response_payload = risk_service.score_account(
        query_text="risk borrower account atlas score",
        limit=3,
    )

    assert response_payload["query"] == "risk borrower account atlas score"
    assert response_payload["total_matches"] >= 1
    assert response_payload["highest_risk_score"] >= 0
    assert response_payload["profiles"]


def test_operations_service_create_alert_or_action_returns_recommendation() -> None:
    operations_service = OperationsService()

    response_payload = operations_service.create_alert_or_action(
        query_text="alert escalate suspicious risk review",
        limit=3,
    )

    assert response_payload["query"] == "alert escalate suspicious risk review"
    assert response_payload["total_matches"] >= 1
    assert response_payload["recommended_action"] is not None
    assert response_payload["templates"]


def test_registry_dispatches_to_domain_handlers_and_preview_delegate() -> None:
    registry = build_default_registry(
        knowledge_service=KnowledgeService(),
        risk_service=RiskService(),
        trade_service=TradeService(),
        operations_service=OperationsService(),
    )

    knowledge_result = registry.invoke(
        tool_name="knowledge.search",
        request_payload={"query": "policy playbook case review"},
    )
    trade_result = registry.invoke(
        tool_name="trade.query_metrics",
        request_payload={"query": "trade wallet volume gamma"},
    )
    preview_matches = registry.preview_knowledge_matches(
        query_text="policy evidence suspicious trade exposure",
        limit=2,
    )

    assert knowledge_result.invocation_status == "completed"
    assert knowledge_result.response_payload["matches"]
    assert trade_result.invocation_status == "completed"
    assert trade_result.response_payload["snapshots"]
    assert preview_matches
