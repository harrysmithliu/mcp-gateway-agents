from dataclasses import dataclass, field

from frontend.services.api import DEFAULT_API_BASE_URL, build_api_client


@dataclass(frozen=True, slots=True)
class AdminRuntimeStatus:
    observed_at: str
    environment: str
    readiness: dict[str, object] = field(default_factory=dict)
    runtime_mode: dict[str, object] = field(default_factory=dict)
    migration: dict[str, object] = field(default_factory=dict)
    mcp: dict[str, object] = field(default_factory=dict)


def get_admin_runtime_status(
    access_token: str,
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout_seconds: float = 5.0,
) -> AdminRuntimeStatus:
    payload = build_api_client(
        access_token=access_token,
        api_base_url=api_base_url,
        timeout_seconds=timeout_seconds,
    ).get("/admin/runtime-status")
    return AdminRuntimeStatus(
        observed_at=str(payload.get("observed_at", "")),
        environment=str(payload.get("environment", "unknown")),
        readiness=dict(payload.get("readiness", {})),
        runtime_mode=dict(payload.get("runtime_mode", {})),
        migration=dict(payload.get("migration", {})),
        mcp=dict(payload.get("mcp", {})),
    )
