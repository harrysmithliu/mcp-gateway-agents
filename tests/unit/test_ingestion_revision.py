from backend.retrieval.ingestion_loader import DEFAULT_CHUNKING_CONFIG
from backend.retrieval.ingestion_models import EmbeddingConfig
from backend.retrieval.ingestion_revision import build_index_fingerprint


def test_index_fingerprint_is_stable_for_same_pipeline_inputs() -> None:
    embedding_config = EmbeddingConfig(
        provider="local_sentence_transformer",
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        vector_dimensions=384,
    )

    first = build_index_fingerprint(
        content_checksum_sha256="a" * 64,
        chunking_config=DEFAULT_CHUNKING_CONFIG,
        embedding_config=embedding_config,
        embedding_normalize=True,
    )
    second = build_index_fingerprint(
        content_checksum_sha256="a" * 64,
        chunking_config=DEFAULT_CHUNKING_CONFIG,
        embedding_config=embedding_config,
        embedding_normalize=True,
    )

    assert first == second
    assert len(first) == 64


def test_index_fingerprint_changes_when_content_or_embedding_changes() -> None:
    base_config = EmbeddingConfig(
        provider="local_sentence_transformer",
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        vector_dimensions=384,
    )
    changed_config = EmbeddingConfig(
        provider="local_sentence_transformer",
        model_name="another-model",
        vector_dimensions=384,
    )

    base = build_index_fingerprint(
        content_checksum_sha256="a" * 64,
        chunking_config=DEFAULT_CHUNKING_CONFIG,
        embedding_config=base_config,
        embedding_normalize=True,
    )
    changed_content = build_index_fingerprint(
        content_checksum_sha256="b" * 64,
        chunking_config=DEFAULT_CHUNKING_CONFIG,
        embedding_config=base_config,
        embedding_normalize=True,
    )
    changed_embedding = build_index_fingerprint(
        content_checksum_sha256="a" * 64,
        chunking_config=DEFAULT_CHUNKING_CONFIG,
        embedding_config=changed_config,
        embedding_normalize=True,
    )

    assert base != changed_content
    assert base != changed_embedding
