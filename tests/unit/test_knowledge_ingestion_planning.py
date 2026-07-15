from backend.services.knowledge_ingestion_planning import (
    build_knowledge_ingestion_change_plan,
)
from backend.storage.models import KnowledgeIngestionSourceRecord


def source(source_id: str, fingerprint: str) -> KnowledgeIngestionSourceRecord:
    return KnowledgeIngestionSourceRecord(
        run_id="run-current",
        source_id=source_id,
        title=source_id,
        source_path=f"data/{source_id}.md",
        checksum_sha256="a" * 64,
        byte_size=10,
        content_type="text/markdown",
        access_level="internal",
        index_fingerprint=fingerprint,
    )


def test_change_plan_classifies_source_revisions_and_removals() -> None:
    plan = build_knowledge_ingestion_change_plan(
        current_sources=(source("new", "new-fingerprint"), source("same", "same"), source("changed", "new")),
        previous_sources=[
            {"source_id": "same", "index_fingerprint": "same"},
            {"source_id": "changed", "index_fingerprint": "old"},
            {"source_id": "removed", "index_fingerprint": "removed"},
        ],
        previous_run={
            "embedding_provider": "local_sentence_transformer",
            "embedding_model_name": "model",
            "vector_dimensions": 384,
        },
        current_embedding_provider="local_sentence_transformer",
        current_embedding_model_name="model",
        current_vector_dimensions=384,
    )

    assert plan.new_source_ids == ("new",)
    assert plan.changed_source_ids == ("changed",)
    assert plan.unchanged_source_ids == ("same",)
    assert plan.removed_source_ids == ("removed",)
    assert plan.source_ids_to_reindex == ("changed", "new")
    assert plan.summary() == {
        "new_source_count": 1,
        "changed_source_count": 1,
        "unchanged_source_count": 1,
        "removed_source_count": 1,
        "reindexed_source_count": 2,
        "embedding_config_changed": False,
        "no_op": False,
    }


def test_embedding_configuration_change_reindexes_all_current_sources() -> None:
    plan = build_knowledge_ingestion_change_plan(
        current_sources=(source("same", "same"),),
        previous_sources=[{"source_id": "same", "index_fingerprint": "same"}],
        previous_run={
            "embedding_provider": "mock",
            "embedding_model_name": "old-model",
            "vector_dimensions": 4,
        },
        current_embedding_provider="local_sentence_transformer",
        current_embedding_model_name="model",
        current_vector_dimensions=384,
    )

    assert plan.embedding_config_changed is True
    assert plan.source_ids_to_reindex == ("same",)
    assert plan.is_no_op is False


def test_first_refresh_marks_all_sources_new() -> None:
    plan = build_knowledge_ingestion_change_plan(
        current_sources=(source("one", "one"), source("two", "two")),
        previous_sources=[],
        previous_run=None,
        current_embedding_provider="mock",
        current_embedding_model_name="mock-model",
        current_vector_dimensions=4,
    )

    assert plan.new_source_ids == ("one", "two")
    assert plan.source_ids_to_reindex == ("one", "two")
