from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.smoke.http_helpers import assert_success, build_demo_client


def test_admin_can_review_knowledge_runs_and_mcp_status() -> None:
    client = build_demo_client("admin_demo")

    ingestion_payload = assert_success(
        client.get("/admin/knowledge/ingestion-runs?limit=5")
    )
    assert ingestion_payload["limit"] == 5
    assert ingestion_payload["query_status"] in {"completed", "degraded"}
    assert isinstance(ingestion_payload["runs"], list)

    mcp_payload = assert_success(client.get("/mcp/sdk-status"))
    assert mcp_payload["transport_mode"] == "registry"
    assert mcp_payload["server_runtime"] == "preview"
    assert mcp_payload["sdk_tool_names"] == ["knowledge.search"]


def test_admin_knowledge_run_detail_preserves_not_found_contract() -> None:
    client = build_demo_client("admin_demo")

    response = client.get(
        "/admin/knowledge/ingestion-runs/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Ingestion run not found"


def test_non_admin_cannot_use_admin_knowledge_or_mcp_status() -> None:
    client = build_demo_client("analyst_demo")

    ingestion_response = client.get("/admin/knowledge/ingestion-runs")
    mcp_response = client.get("/mcp/sdk-status")

    assert ingestion_response.status_code == 403
    assert mcp_response.status_code == 403
