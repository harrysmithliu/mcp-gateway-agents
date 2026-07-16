from __future__ import annotations

import json
from pathlib import Path
import sys
from urllib import error, request


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.db import DatabaseClient, DatabaseConfig
from backend.storage.redis_chat_context import RedisChatContextStore
from backend.storage.settings import get_settings
from frontend.services.chat import post_chat_message


DEMO_USERNAME = "risk_operator_demo"
DEMO_PASSWORD = "demo-password"


def check_api_health(api_base_url: str) -> dict[str, object]:
    try:
        with request.urlopen(f"{api_base_url}/health", timeout=5.0) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.URLError as exc:
        raise RuntimeError(
            f"Unable to reach the backend health endpoint at {api_base_url}/health."
        ) from exc


def login(api_base_url: str) -> str:
    payload = json.dumps(
        {"username": DEMO_USERNAME, "password": DEMO_PASSWORD}
    ).encode("utf-8")
    login_request = request.Request(
        url=f"{api_base_url.rstrip('/')}/auth/login",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(login_request, timeout=5.0) as response:
            login_payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        raise RuntimeError(
            f"Demo login failed with HTTP {exc.code}."
        ) from exc
    except error.URLError as exc:
        raise RuntimeError(f"Unable to reach the login endpoint at {api_base_url}.") from exc
    access_token = login_payload.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise RuntimeError("Demo login did not return an access token.")
    return access_token


def check_database_connection(database_client: DatabaseClient) -> None:
    try:
        with database_client.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
    except Exception as exc:
        raise RuntimeError(
            "Unable to reach PostgreSQL. Verify the database runtime is up and DATABASE_URL is correct."
        ) from exc


def check_redis_connection(redis_store: RedisChatContextStore) -> None:
    try:
        redis_store._get_client().ping()
    except Exception as exc:
        raise RuntimeError(
            "Unable to reach Redis. Verify the Redis runtime is up and REDIS_URL is correct."
        ) from exc


def query_single_value(
    database_client: DatabaseClient,
    sql: str,
    params: dict[str, object],
) -> int:
    with database_client.connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
    return int(row[0]) if row is not None else 0


def build_session_persistence_report(
    database_client: DatabaseClient,
    session_id: str,
) -> dict[str, int]:
    return {
        "chat_sessions": query_single_value(
            database_client,
            "SELECT COUNT(*) FROM convo.chat_sessions WHERE session_id = %(session_id)s",
            {"session_id": session_id},
        ),
        "chat_messages": query_single_value(
            database_client,
            "SELECT COUNT(*) FROM convo.chat_messages WHERE session_id = %(session_id)s",
            {"session_id": session_id},
        ),
        "tool_call_logs": query_single_value(
            database_client,
            "SELECT COUNT(*) FROM audit.tool_call_logs WHERE session_id = %(session_id)s",
            {"session_id": session_id},
        ),
        "audit_events": query_single_value(
            database_client,
            "SELECT COUNT(*) FROM audit.audit_events "
            "WHERE event_payload->>'session_id' = %(session_id)s",
            {"session_id": session_id},
        ),
        "risk_alerts": query_single_value(
            database_client,
            "SELECT COUNT(*) FROM risk.risk_alerts WHERE session_id = %(session_id)s",
            {"session_id": session_id},
        ),
    }


def main() -> int:
    settings = get_settings()
    api_base_url = f"http://{settings.api_host}:{settings.api_port}"
    database_client = DatabaseClient(
        DatabaseConfig(database_url=settings.database_url)
    )
    redis_store = RedisChatContextStore(redis_url=settings.redis_url)
    health_payload = check_api_health(api_base_url)
    access_token = login(api_base_url)
    check_database_connection(database_client)
    check_redis_connection(redis_store)

    first_response = post_chat_message(
        user_role="risk_operator",
        message_text=(
            "Please search the policy playbook, score this borrower account, "
            "review the trade wallet volume gamma, and create an alert for this suspicious risk review."
        ),
        api_base_url=api_base_url,
        timeout_seconds=120.0,
        access_token=access_token,
    )
    if first_response.session_id is None:
        raise RuntimeError("Chat API did not return a session_id.")

    second_response = post_chat_message(
        user_role="risk_operator",
        message_text="Give me the next monitoring step for this same case.",
        session_id=first_response.session_id,
        api_base_url=api_base_url,
        timeout_seconds=120.0,
        access_token=access_token,
    )

    redis_messages = redis_store.load_recent_messages(
        first_response.session_id,
        user_id=2,
    )
    persistence_report = build_session_persistence_report(
        database_client=database_client,
        session_id=first_response.session_id,
    )

    if persistence_report["chat_sessions"] < 1:
        raise RuntimeError("Expected at least one persisted chat session.")
    if persistence_report["chat_messages"] < 4:
        raise RuntimeError("Expected at least four persisted chat messages across two turns.")
    if persistence_report["tool_call_logs"] < 1:
        raise RuntimeError("Expected persisted tool invocation logs for the verification session.")
    if persistence_report["audit_events"] < 1:
        raise RuntimeError("Expected persisted audit events for the verification session.")
    blocked_action = next(
        (
            result
            for result in first_response.tool_invocation_results
            if result.tool_name == "ops.create_alert_or_action"
        ),
        None,
    )
    if blocked_action is None or blocked_action.invocation_status != "blocked":
        raise RuntimeError(
            "Expected the high-impact operations action to be blocked before invocation."
        )
    if persistence_report["risk_alerts"] != 0:
        raise RuntimeError(
            "A blocked chat action must not create an operational alert record."
        )
    if len(redis_messages) < 2:
        raise RuntimeError("Expected Redis short-term context to contain persisted chat messages.")

    print(
        json.dumps(
            {
                "api_base_url": api_base_url,
                "health": health_payload,
                "session_id": first_response.session_id,
                "first_turn_tool_names": first_response.tool_names,
                "second_turn_tool_names": second_response.tool_names,
                "redis_message_count": len(redis_messages),
                "postgres_persistence": persistence_report,
                "blocked_action": blocked_action.invocation_status,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
