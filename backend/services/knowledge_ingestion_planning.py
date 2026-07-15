from dataclasses import dataclass

from backend.storage.models import KnowledgeIngestionSourceRecord


@dataclass(frozen=True, slots=True)
class KnowledgeIngestionChangePlan:
    """Pure refresh decision produced before any knowledge data is written."""

    new_source_ids: tuple[str, ...]
    changed_source_ids: tuple[str, ...]
    unchanged_source_ids: tuple[str, ...]
    removed_source_ids: tuple[str, ...]
    source_ids_to_reindex: tuple[str, ...]
    embedding_config_changed: bool = False

    @property
    def is_no_op(self) -> bool:
        return not self.source_ids_to_reindex and not self.removed_source_ids

    def summary(self) -> dict[str, object]:
        return {
            "new_source_count": len(self.new_source_ids),
            "changed_source_count": len(self.changed_source_ids),
            "unchanged_source_count": len(self.unchanged_source_ids),
            "removed_source_count": len(self.removed_source_ids),
            "reindexed_source_count": len(self.source_ids_to_reindex),
            "embedding_config_changed": self.embedding_config_changed,
            "no_op": self.is_no_op,
        }


def build_knowledge_ingestion_change_plan(
    current_sources: tuple[KnowledgeIngestionSourceRecord, ...],
    previous_sources: list[dict[str, object]],
    previous_run: dict[str, object] | None,
    current_embedding_provider: str,
    current_embedding_model_name: str,
    current_vector_dimensions: int,
) -> KnowledgeIngestionChangePlan:
    """Compares source revisions and embedding settings without performing writes."""

    previous_by_source_id = {
        str(source["source_id"]): source for source in previous_sources
    }
    current_by_source_id = {source.source_id: source for source in current_sources}

    new_source_ids = tuple(
        sorted(source_id for source_id in current_by_source_id if source_id not in previous_by_source_id)
    )
    changed_source_ids = tuple(
        sorted(
            source_id
            for source_id, source in current_by_source_id.items()
            if source_id in previous_by_source_id
            and source.index_fingerprint
            != previous_by_source_id[source_id].get("index_fingerprint")
        )
    )
    unchanged_source_ids = tuple(
        sorted(
            source_id
            for source_id, source in current_by_source_id.items()
            if source_id in previous_by_source_id
            and source.index_fingerprint
            == previous_by_source_id[source_id].get("index_fingerprint")
        )
    )
    removed_source_ids = tuple(
        sorted(source_id for source_id in previous_by_source_id if source_id not in current_by_source_id)
    )

    embedding_config_changed = bool(
        previous_run
        and (
            previous_run.get("embedding_provider") != current_embedding_provider
            or previous_run.get("embedding_model_name") != current_embedding_model_name
            or previous_run.get("vector_dimensions") != current_vector_dimensions
        )
    )
    source_ids_to_reindex = tuple(
        sorted(
            current_by_source_id
            if embedding_config_changed
            else set(new_source_ids).union(changed_source_ids)
        )
    )

    return KnowledgeIngestionChangePlan(
        new_source_ids=new_source_ids,
        changed_source_ids=changed_source_ids,
        unchanged_source_ids=unchanged_source_ids,
        removed_source_ids=removed_source_ids,
        source_ids_to_reindex=source_ids_to_reindex,
        embedding_config_changed=embedding_config_changed,
    )
