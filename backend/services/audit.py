from dataclasses import dataclass

from backend.storage.runtime import StorageBundle


@dataclass(slots=True)
class AuditService:
    storage_bundle: StorageBundle

    def list_recent_events(
        self,
        limit: int = 10,
        event_type: str | None = None,
        session_id: str | None = None,
        actor_user_id: int | None = None,
    ) -> dict[str, object]:
        try:
            events = self.storage_bundle.audit_event_repository.list_recent_events(
                limit=limit,
                event_type=event_type,
                session_id=session_id,
                actor_user_id=actor_user_id,
            )
            return {
                "limit": limit,
                "event_type": event_type,
                "session_id": session_id,
                "actor_user_id": actor_user_id,
                "query_status": "completed",
                "events": events,
            }
        except Exception:
            return {
                "limit": limit,
                "event_type": event_type,
                "session_id": session_id,
                "actor_user_id": actor_user_id,
                "query_status": "degraded",
                "events": [],
            }

    def list_tool_invocations(
        self,
        limit: int = 10,
        session_id: str | None = None,
        tool_name: str | None = None,
        call_status: str | None = None,
    ) -> dict[str, object]:
        try:
            tool_calls = self.storage_bundle.tool_call_log_repository.list_recent_tool_calls(
                limit=limit,
                session_id=session_id,
                tool_name=tool_name,
                call_status=call_status,
            )
            return {
                "limit": limit,
                "session_id": session_id,
                "tool_name": tool_name,
                "call_status": call_status,
                "query_status": "completed",
                "tool_calls": tool_calls,
            }
        except Exception:
            return {
                "limit": limit,
                "session_id": session_id,
                "tool_name": tool_name,
                "call_status": call_status,
                "query_status": "degraded",
                "tool_calls": [],
            }
