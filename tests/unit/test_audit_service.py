from dataclasses import dataclass

from backend.services.audit import AuditService


@dataclass(slots=True)
class FakeAuditEventRepository:
    events: list[dict[str, object]]

    def list_recent_events(
        self,
        limit: int = 10,
        event_type: str | None = None,
    ) -> list[dict[str, object]]:
        if event_type is None:
            return self.events[:limit]
        return [
            event
            for event in self.events
            if event["event_type"] == event_type
        ][:limit]


@dataclass(slots=True)
class FakeStorageBundle:
    audit_event_repository: FakeAuditEventRepository


def test_audit_service_returns_recent_events_payload() -> None:
    service = AuditService(
        storage_bundle=FakeStorageBundle(
            audit_event_repository=FakeAuditEventRepository(
                events=[
                    {"event_id": "evt-1", "event_type": "tool_invocation"},
                    {"event_id": "evt-2", "event_type": "chat_completion"},
                ]
            )
        )
    )

    response_payload = service.list_recent_events(limit=1)

    assert response_payload["query_status"] == "completed"
    assert len(response_payload["events"]) == 1
    assert response_payload["events"][0]["event_id"] == "evt-1"
