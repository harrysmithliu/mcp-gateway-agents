from dataclasses import asdict, dataclass

from backend.auth.models import IdentityPrincipal


@dataclass(frozen=True, slots=True)
class AuthorizationContext:
    """Server-derived authorization metadata passed to RAG and MCP tools."""

    user_id: int
    username: str
    roles: tuple[str, ...]
    access_level: str
    allowed_access_levels: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.allowed_access_levels:
            object.__setattr__(self, "allowed_access_levels", (self.access_level,))

    @classmethod
    def from_principal(cls, principal: IdentityPrincipal) -> "AuthorizationContext":
        is_admin = "admin" in principal.roles
        access_level = "restricted" if is_admin else "internal"
        return cls(
            user_id=principal.user_id,
            username=principal.user.username,
            roles=principal.roles,
            access_level=access_level,
            allowed_access_levels=("internal", "restricted") if is_admin else ("internal",),
        )

    def to_payload(self) -> dict[str, object]:
        return asdict(self)
