from pwdlib import PasswordHash


class PasswordService:
    """Argon2 password hashing boundary for provisioned local identities."""

    def __init__(self, password_hash: PasswordHash | None = None) -> None:
        self._password_hash = password_hash or PasswordHash.recommended()

    def hash_password(self, password: str) -> str:
        if not password:
            raise ValueError("Password must not be empty.")
        return self._password_hash.hash(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        if not password or not password_hash:
            return False
        return self._password_hash.verify(password, password_hash)
