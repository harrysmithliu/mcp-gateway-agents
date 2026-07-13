from dataclasses import dataclass, field

from backend.services.audit import AuditService


@dataclass(slots=True)
class FakeAuditEventRepository:
    events: list[dict[str, object]]

    def list_recent_events(
        self,
        limit: int = 10,
        event_type: str | None = None,
        session_id: str | None = None,
        actor_user_id: int | None = None,
    ) -> list[dict[str, object]]:
        if event_type is None:
            return self.events[:limit]
        return [
            event
            for event in self.events
            if event["event_type"] == event_type
        ][:limit]


@dataclass(slots=True)
class FakeToolCallLogRepository:
    def list_recent_tool_calls(
        self,
        limit: int = 10,
        session_id: str | None = None,
        tool_name: str | None = None,
        call_status: str | None = None,
    ) -> list[dict[str, object]]:
        return [
            {
                "tool_call_id": "call-1",
                "session_id": session_id,
                "tool_name": tool_name or "knowledge.search",
                "call_status": call_status or "completed",
            }
        ][:limit]


@dataclass(slots=True)
class FakeStorageBundle:
    audit_event_repository: FakeAuditEventRepository
    tool_call_log_repository: FakeToolCallLogRepository = field(
        default_factory=FakeToolCallLogRepository
    )


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


def test_audit_service_returns_tool_invocation_read_model() -> None:
    service = AuditService(
        storage_bundle=FakeStorageBundle(
            audit_event_repository=FakeAuditEventRepository(events=[])
        )
    )

    response_payload = service.list_tool_invocations(
        limit=5,
        session_id="session-1",
        tool_name="knowledge.search",
        call_status="completed",
    )

    assert response_payload["query_status"] == "completed"
    assert response_payload["tool_calls"][0]["tool_name"] == "knowledge.search"
