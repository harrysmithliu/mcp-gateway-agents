from backend.storage.settings import Settings


def test_auth_settings_have_local_jwt_defaults() -> None:
    settings = Settings(
        auth_mode="local_jwt",
        auth_jwt_secret="local-test-secret",
        auth_jwt_issuer="test-issuer",
        auth_jwt_audience="test-audience",
        auth_access_token_ttl_seconds=900,
        auth_allow_multiple_identities=False,
    )

    assert settings.auth_mode == "local_jwt"
    assert settings.auth_jwt_secret == "local-test-secret"
    assert settings.auth_jwt_issuer == "test-issuer"
    assert settings.auth_jwt_audience == "test-audience"
    assert settings.auth_access_token_ttl_seconds == 900
    assert settings.auth_allow_multiple_identities is False
