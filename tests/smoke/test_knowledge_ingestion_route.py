from fastapi.testclient import TestClient

from backend.api.app import app


def test_knowledge_ingestion_route_is_admin_only() -> None:
    client = TestClient(app)

    analyst_response = client.get(
        "/admin/knowledge/ingestion-runs",
        headers={"x-demo-user": "analyst_demo"},
    )
    admin_response = client.get(
        "/admin/knowledge/ingestion-runs",
        headers={"x-demo-user": "admin_demo"},
    )

    assert analyst_response.status_code == 403
    assert admin_response.status_code == 200
    assert admin_response.json()["query_status"] in {"completed", "degraded"}
    assert isinstance(admin_response.json()["runs"], list)
