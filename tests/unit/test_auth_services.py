from datetime import datetime, timezone

import pytest

from backend.auth.passwords import PasswordService
from backend.auth.tokens import JWTTokenService, TokenValidationError


def test_password_service_hashes_and_verifies_password() -> None:
    service = PasswordService()
    password_hash = service.hash_password("local-password")

    assert password_hash != "local-password"
    assert service.verify_password("local-password", password_hash) is True
    assert service.verify_password("wrong-password", password_hash) is False


def test_jwt_token_service_round_trips_required_identity_claims() -> None:
    service = JWTTokenService(
        secret="local-test-secret-with-at-least-32-bytes",
        issuer="test-issuer",
        audience="test-audience",
        ttl_seconds=900,
    )
    issued_at = datetime.now(timezone.utc)

    token = service.issue_token(
        user_id=7,
        auth_session_id="session-1",
        token_jti="jti-1",
        now=issued_at,
    )
    claims = service.decode_token(token)

    assert claims["sub"] == "7"
    assert claims["sid"] == "session-1"
    assert claims["jti"] == "jti-1"
    assert claims["iss"] == "test-issuer"
    assert claims["aud"] == "test-audience"


def test_jwt_token_service_rejects_wrong_secret() -> None:
    service = JWTTokenService(
        secret="local-test-secret-with-at-least-32-bytes",
        issuer="test-issuer",
        audience="test-audience",
        ttl_seconds=900,
    )
    token = service.issue_token(7, "session-1", "jti-1")
    invalid_service = JWTTokenService(
        secret="other-secret-with-at-least-32-bytes",
        issuer="test-issuer",
        audience="test-audience",
        ttl_seconds=900,
    )

    with pytest.raises(TokenValidationError):
        invalid_service.decode_token(token)
