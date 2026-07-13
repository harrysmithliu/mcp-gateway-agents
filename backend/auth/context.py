from dataclasses import asdict, dataclass

from backend.auth.models import IdentityPrincipal


@dataclass(frozen=True, slots=True)
class AuthorizationContext:
    """Server-derived authorization metadata passed to RAG and MCP tools."""

    user_id: int
    username: str
    roles: tuple[str, ...]
    access_level: str

    @classmethod
    def from_principal(cls, principal: IdentityPrincipal) -> "AuthorizationContext":
        access_level = "restricted" if "admin" in principal.roles else "internal"
        return cls(
            user_id=principal.user_id,
            username=principal.user.username,
            roles=principal.roles,
            access_level=access_level,
        )

    def to_payload(self) -> dict[str, object]:
        return asdict(self)
