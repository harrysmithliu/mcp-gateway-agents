from fastapi import APIRouter

from backend.auth.rbac import list_demo_users

router = APIRouter(tags=["auth"])


@router.get("/auth/demo-users")
def get_demo_users() -> dict[str, object]:
    return {
        "default_user": "analyst_demo",
        "users": list_demo_users(),
    }
