from datetime import datetime, timedelta, timezone
from typing import Any

import jwt


class TokenValidationError(ValueError):
    """Raised when a bearer token fails the configured JWT contract."""


class JWTTokenService:
    algorithm = "HS256"

    def __init__(
        self,
        secret: str,
        issuer: str,
        audience: str,
        ttl_seconds: int,
    ) -> None:
        if not secret:
            raise ValueError("AUTH_JWT_SECRET must be configured.")
        self.secret = secret
        self.issuer = issuer
        self.audience = audience
        self.ttl_seconds = ttl_seconds

    def issue_token(
        self,
        user_id: int,
        auth_session_id: str,
        token_jti: str,
        now: datetime | None = None,
    ) -> str:
        issued_at = now or datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "sid": auth_session_id,
            "jti": token_jti,
            "iss": self.issuer,
            "aud": self.audience,
            "iat": issued_at,
            "exp": issued_at + timedelta(seconds=self.ttl_seconds),
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def decode_token(self, token: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm],
                issuer=self.issuer,
                audience=self.audience,
                options={"require": ["sub", "sid", "jti", "iss", "aud", "iat", "exp"]},
            )
        except jwt.PyJWTError as exc:
            raise TokenValidationError("Invalid bearer token.") from exc
        return payload
