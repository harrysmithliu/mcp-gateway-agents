from dataclasses import dataclass
from uuid import uuid4

from backend.observability.context import get_request_id
from backend.storage.models import AuditEventRecord
from backend.storage.repositories.audit_events import AuditEventRepository
from backend.storage.repositories.runtime_switches import RuntimeSwitchRepository


class RuntimeSwitchError(ValueError):
    """Raised when an administrator targets an unsupported runtime switch."""


@dataclass(frozen=True, slots=True)
class RuntimeSwitchDefinition:
    key: str
    default_enabled: bool
    description: str


RUNTIME_SWITCH_DEFINITIONS = (
    RuntimeSwitchDefinition(
        key="maintenance_mode",
        default_enabled=False,
        description="Temporarily block non-admin application workflows.",
    ),
    RuntimeSwitchDefinition(
        key="response_cache_enabled",
        default_enabled=True,
        description="Allow eligible read-only agent responses to use Redis caching.",
    ),
    RuntimeSwitchDefinition(
        key="retrieval_enabled",
        default_enabled=True,
        description="Allow RAG retrieval to query the configured pgvector knowledge base.",
    ),
)
_DEFINITIONS_BY_KEY = {definition.key: definition for definition in RUNTIME_SWITCH_DEFINITIONS}


@dataclass(frozen=True, slots=True)
class RuntimeSwitchState:
    key: str
    is_enabled: bool
    default_enabled: bool
    description: str

    def to_payload(self) -> dict[str, object]:
        return {
            "key": self.key,
            "is_enabled": self.is_enabled,
            "default_enabled": self.default_enabled,
            "description": self.description,
        }


@dataclass(slots=True)
class RuntimeSwitchService:
    """Allowlisted, audit-backed runtime feature controls with safe read fallback."""

    database_client: object
    runtime_switch_repository: RuntimeSwitchRepository
    audit_event_repository: AuditEventRepository

    def list_switches(self) -> list[RuntimeSwitchState]:
        persisted_by_key = {
            str(row["switch_key"]): bool(row["is_enabled"])
            for row in self.runtime_switch_repository.list_runtime_switches()
        }
        return [
            RuntimeSwitchState(
                key=definition.key,
                is_enabled=persisted_by_key.get(
                    definition.key,
                    definition.default_enabled,
                ),
                default_enabled=definition.default_enabled,
                description=definition.description,
            )
            for definition in RUNTIME_SWITCH_DEFINITIONS
        ]

    def is_enabled(self, key: str, default: bool) -> bool:
        """Read a persisted allowlisted override without failing application traffic."""

        definition = _DEFINITIONS_BY_KEY.get(key)
        if definition is None:
            return default
        try:
            states = {state.key: state for state in self.list_switches()}
            return states[key].is_enabled
        except Exception:
            return default

    def set_enabled(
        self,
        *,
        key: str,
        is_enabled: bool,
        actor_user_id: int,
    ) -> RuntimeSwitchState:
        definition = _DEFINITIONS_BY_KEY.get(key)
        if definition is None:
            raise RuntimeSwitchError("Unsupported runtime switch.")
        with self.database_client.transaction() as transaction:
            transaction.execute(
                self.runtime_switch_repository.build_set_statement(
                    switch_key=key,
                    is_enabled=is_enabled,
                    actor_user_id=actor_user_id,
                )
            )
            transaction.execute(
                self.audit_event_repository.build_create_statement(
                    AuditEventRecord(
                        event_id=str(uuid4()),
                        actor_user_id=actor_user_id,
                        request_id=get_request_id(),
                        event_type="admin_runtime_switch_updated",
                        event_summary="Administrator updated a runtime switch.",
                        event_payload={"switch_key": key, "is_enabled": is_enabled},
                    )
                )
            )
        return RuntimeSwitchState(
            key=definition.key,
            is_enabled=is_enabled,
            default_enabled=definition.default_enabled,
            description=definition.description,
        )
