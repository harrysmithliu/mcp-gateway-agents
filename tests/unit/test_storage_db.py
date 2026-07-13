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


class FakeCursor:
    def __init__(self, connection: "FakeConnection") -> None:
        self.connection = connection
        self.description = None

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, sql: str, params: dict[str, object]) -> None:
        self.connection.executed.append((sql, params))


class FakeConnection:
    def __init__(self) -> None:
        self.executed: list[tuple[str, dict[str, object]]] = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


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


def test_database_client_transaction_commits_related_statements(monkeypatch) -> None:
    client = DatabaseClient(
        config=DatabaseConfig(database_url="postgresql://example")
    )
    connection = FakeConnection()
    monkeypatch.setattr(DatabaseClient, "_import_psycopg", lambda self: FakePsycopg)
    monkeypatch.setattr(
        DatabaseClient,
        "connect",
        lambda self: _connection_context(connection),
    )

    with client.transaction() as transaction:
        transaction.execute(SQLStatement(sql="SELECT 1", params={}))
        transaction.execute(SQLStatement(sql="SELECT 2", params={}))

    assert [sql for sql, _ in connection.executed] == ["SELECT 1", "SELECT 2"]
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert connection.closed is True


def test_database_client_transaction_rolls_back_on_failure(monkeypatch) -> None:
    client = DatabaseClient(
        config=DatabaseConfig(database_url="postgresql://example")
    )
    connection = FakeConnection()
    monkeypatch.setattr(DatabaseClient, "_import_psycopg", lambda self: FakePsycopg)
    monkeypatch.setattr(
        DatabaseClient,
        "connect",
        lambda self: _connection_context(connection),
    )

    try:
        with client.transaction() as transaction:
            transaction.execute(SQLStatement(sql="SELECT 1", params={}))
            raise ValueError("transaction failure")
    except ValueError:
        pass

    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.closed is True


class _connection_context:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection

    def __enter__(self) -> FakeConnection:
        return self.connection

    def __exit__(self, *args: object) -> None:
        self.connection.close()
