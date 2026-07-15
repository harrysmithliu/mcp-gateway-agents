import json
from hashlib import sha256

from backend.retrieval.ingestion_models import ChunkingConfig, EmbeddingConfig


def build_index_fingerprint(
    content_checksum_sha256: str,
    chunking_config: ChunkingConfig,
    embedding_config: EmbeddingConfig,
    embedding_normalize: bool,
) -> str:
    """Builds a stable revision key for content and vectorization settings."""

    payload = {
        "content_checksum_sha256": content_checksum_sha256,
        "chunking": {
            "chunk_size": chunking_config.chunk_size,
            "chunk_overlap": chunking_config.chunk_overlap,
            "splitter_type": chunking_config.splitter_type,
        },
        "embedding": {
            "provider": embedding_config.provider,
            "model_name": embedding_config.model_name,
            "vector_dimensions": embedding_config.vector_dimensions,
            "query_prefix": embedding_config.query_prefix,
            "normalize": embedding_normalize,
        },
    }
    canonical_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(canonical_payload.encode("utf-8")).hexdigest()
