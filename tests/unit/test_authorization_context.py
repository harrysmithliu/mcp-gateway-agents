from backend.auth.context import AuthorizationContext
from backend.auth.models import IdentityPrincipal, IdentityUser


def build_principal(*roles: str) -> IdentityPrincipal:
    return IdentityPrincipal(
        user=IdentityUser(
            user_id=7,
            username="demo-user",
            display_name="Demo User",
            is_active=True,
        ),
        roles=roles,
        auth_session_id="auth-session-1",
        browser_session_id="browser-session-1",
    )


def test_admin_context_owns_hierarchical_knowledge_scope() -> None:
    context = AuthorizationContext.from_principal(build_principal("admin"))

    assert context.access_level == "restricted"
    assert context.allowed_access_levels == ("internal", "restricted")


def test_non_admin_context_is_limited_to_internal_knowledge() -> None:
    context = AuthorizationContext.from_principal(build_principal("analyst"))

    assert context.access_level == "internal"
    assert context.allowed_access_levels == ("internal",)
