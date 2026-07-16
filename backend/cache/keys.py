import hashlib
import json

from backend.cache.contracts import CACHE_CONTRACT_VERSION, CacheRequestContext


DEFAULT_CACHE_KEY_PREFIX = "agent:response"


def build_cache_key(
    context: CacheRequestContext,
    key_prefix: str = DEFAULT_CACHE_KEY_PREFIX,
) -> str:
    """Build a deterministic, opaque key bound to identity and context."""

    normalized_prefix = key_prefix.strip()
    if not normalized_prefix:
        raise ValueError("Cache key prefix cannot be empty.")

    key_material = {
        "cache_contract_version": CACHE_CONTRACT_VERSION,
        "response_contract_version": context.response_contract_version,
        "normalized_text": " ".join(context.normalized_text.split()),
        "user_id": context.user_id,
        "role": context.normalized_role.strip().lower(),
        "authorization_scope": list(context.normalized_scope),
        "session_id": context.session_id.strip() if context.session_id else None,
        "history_fingerprint": context.history_fingerprint,
        "context_revision": context.context_revision,
    }
    serialized_material = json.dumps(
        key_material,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(serialized_material).hexdigest()
    return f"{normalized_prefix}:v1:{digest}"
