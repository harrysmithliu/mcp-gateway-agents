from dataclasses import dataclass

from backend.storage.runtime import StorageBundle


@dataclass(slots=True)
class AuditService:
    storage_bundle: StorageBundle

    def list_recent_events(
        self,
        limit: int = 10,
        event_type: str | None = None,
    ) -> dict[str, object]:
        try:
            events = self.storage_bundle.audit_event_repository.list_recent_events(
                limit=limit,
                event_type=event_type,
            )
            return {
                "limit": limit,
                "event_type": event_type,
                "query_status": "completed",
                "events": events,
            }
        except Exception:
            return {
                "limit": limit,
                "event_type": event_type,
                "query_status": "degraded",
                "events": [],
            }
