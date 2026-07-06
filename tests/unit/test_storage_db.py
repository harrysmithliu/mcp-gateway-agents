import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.db import DatabaseClient, DatabaseConfig, SQLStatement


class FakeJsonb:
    def __init__(self, value: object) -> None:
        self.value = value


class FakePsycopg:
    class types:
        class json:
            Jsonb = FakeJsonb


def test_database_client_normalizes_json_like_statement_params() -> None:
    client = DatabaseClient(
        config=DatabaseConfig(database_url="postgresql://example")
    )
    statement = SQLStatement(
        sql="INSERT INTO demo VALUES (%(payload)s, %(count)s, %(items)s)",
        params={
            "payload": {"tool_name": "knowledge.search"},
            "count": 2,
            "items": ["a", "b"],
        },
    )

    normalized_params = client._normalize_statement_params(
        statement=statement,
        psycopg=FakePsycopg,
    )

    assert isinstance(normalized_params["payload"], FakeJsonb)
    assert normalized_params["payload"].value == {"tool_name": "knowledge.search"}
    assert normalized_params["count"] == 2
    assert isinstance(normalized_params["items"], FakeJsonb)
    assert normalized_params["items"].value == ["a", "b"]
