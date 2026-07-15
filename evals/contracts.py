from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Mapping


VALID_INVOCATION_STATUSES = frozenset({"completed", "failed", "unavailable"})
VALID_RETRIEVAL_STATUSES = frozenset(
    {"completed", "empty", "failed", "unavailable", "disabled"}
)


def _normalize_strings(values: object) -> tuple[str, ...]:
    if values is None:
        return ()
    if not isinstance(values, (list, tuple)):
        raise ValueError("evaluation string collections must be lists")
    normalized = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("evaluation string collections must contain non-empty strings")
        normalized.append(value.strip())
    return tuple(dict.fromkeys(normalized))


@dataclass(frozen=True, slots=True)
class EvalCase:
    """Versioned, provider-neutral expectation for one agent evaluation case."""

    case_id: str
    role: str
    message_text: str
    required_tools: tuple[str, ...] = field(default_factory=tuple)
    forbidden_tools: tuple[str, ...] = field(default_factory=tuple)
    expected_citation_chunk_ids: tuple[str, ...] = field(default_factory=tuple)
    requires_rag: bool = False
    expected_invocation_status: str = "completed"
    expected_retrieval_status: str | None = None
    expected_authorization_scope: tuple[str, ...] = field(default_factory=tuple)
    runtime_profile: str = "default"
    tags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        case_id = self.case_id.strip()
        role = self.role.strip().lower()
        message_text = self.message_text.strip()
        runtime_profile = self.runtime_profile.strip().lower()
        if not case_id or not role or not message_text:
            raise ValueError("evaluation case_id, role and message_text are required")
        if not runtime_profile:
            raise ValueError("evaluation runtime_profile must not be empty")
        if self.expected_invocation_status not in VALID_INVOCATION_STATUSES:
            raise ValueError("evaluation case has an invalid invocation status")
        if (
            self.expected_retrieval_status is not None
            and self.expected_retrieval_status not in VALID_RETRIEVAL_STATUSES
        ):
            raise ValueError("evaluation case has an invalid retrieval status")
        required_tools = tuple(dict.fromkeys(self.required_tools))
        forbidden_tools = tuple(dict.fromkeys(self.forbidden_tools))
        if set(required_tools).intersection(forbidden_tools):
            raise ValueError("a tool cannot be both required and forbidden")
        if self.requires_rag and not self.expected_citation_chunk_ids:
            raise ValueError("RAG cases must define expected citation chunk ids")
        object.__setattr__(self, "case_id", case_id)
        object.__setattr__(self, "role", role)
        object.__setattr__(self, "message_text", message_text)
        object.__setattr__(self, "runtime_profile", runtime_profile)
        object.__setattr__(self, "required_tools", required_tools)
        object.__setattr__(self, "forbidden_tools", forbidden_tools)
        object.__setattr__(
            self,
            "expected_citation_chunk_ids",
            tuple(dict.fromkeys(self.expected_citation_chunk_ids)),
        )
        object.__setattr__(
            self,
            "expected_authorization_scope",
            tuple(dict.fromkeys(self.expected_authorization_scope)),
        )
        object.__setattr__(self, "tags", tuple(dict.fromkeys(self.tags)))

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> "EvalCase":
        return cls(
            case_id=_required_string(payload, "case_id"),
            role=_required_string(payload, "role"),
            message_text=_required_string(payload, "message_text"),
            required_tools=_normalize_strings(payload.get("required_tools")),
            forbidden_tools=_normalize_strings(payload.get("forbidden_tools")),
            expected_citation_chunk_ids=_normalize_strings(
                payload.get("expected_citation_chunk_ids")
            ),
            requires_rag=bool(payload.get("requires_rag", False)),
            expected_invocation_status=str(
                payload.get("expected_invocation_status", "completed")
            ),
            expected_retrieval_status=(
                str(payload["expected_retrieval_status"])
                if payload.get("expected_retrieval_status") is not None
                else None
            ),
            expected_authorization_scope=_normalize_strings(
                payload.get("expected_authorization_scope")
            ),
            runtime_profile=str(payload.get("runtime_profile", "default")),
            tags=_normalize_strings(payload.get("tags")),
        )

    def to_payload(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EvalObservation:
    """Provider-neutral observation captured from one target execution."""

    case_id: str
    tool_names: tuple[str, ...] = field(default_factory=tuple)
    invocation_statuses: tuple[str, ...] = field(default_factory=tuple)
    citation_chunk_ids: tuple[str, ...] = field(default_factory=tuple)
    retrieval_status: str | None = None
    authorization_scope: tuple[str, ...] = field(default_factory=tuple)
    citation_schema_valid: bool = True
    latency_ms: int = 0
    error: str | None = None


@dataclass(frozen=True, slots=True)
class EvalScore:
    """Deterministic score for one case, with hard checks kept explicit."""

    case_id: str
    passed: bool
    checks: dict[str, bool] = field(default_factory=dict)
    tool_recall: float = 0.0
    citation_coverage: float = 0.0
    latency_ms: int = 0
    error: str | None = None


@dataclass(frozen=True, slots=True)
class EvalReport:
    """Machine-readable aggregate report for one evaluation dataset run."""

    dataset_name: str
    dataset_version: str
    scores: tuple[EvalScore, ...] = field(default_factory=tuple)
    summary: dict[str, object] = field(default_factory=dict)

    def to_payload(self) -> dict[str, object]:
        return {
            "dataset_name": self.dataset_name,
            "dataset_version": self.dataset_version,
            "scores": [asdict(score) for score in self.scores],
            "summary": dict(self.summary),
        }


def _required_string(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"evaluation case requires non-empty {key}")
    return value
