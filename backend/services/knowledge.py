from dataclasses import dataclass

from backend.services.demo_data import load_demo_dataset
from backend.services.common import tokenize_text


@dataclass(frozen=True, slots=True)
class KnowledgeRecord:
    document_id: str
    title: str
    summary: str
    keywords: tuple[str, ...]


DEFAULT_KNOWLEDGE_RECORDS = tuple(
    KnowledgeRecord(
        document_id=str(record["document_id"]),
        title=str(record["title"]),
        summary=str(record["summary"]),
        keywords=tuple(str(keyword) for keyword in record["keywords"]),
    )
    for record in load_demo_dataset("knowledge")
)


@dataclass(slots=True)
class KnowledgeService:
    records: tuple[KnowledgeRecord, ...] = DEFAULT_KNOWLEDGE_RECORDS

    def preview_matches(
        self,
        query_text: str,
        limit: int = 3,
    ) -> list[dict[str, object]]:
        query_terms = tokenize_text(query_text)
        ranked_matches = []

        for record in self.records:
            matched_terms = sorted(query_terms.intersection(record.keywords))
            if not matched_terms:
                continue

            ranked_matches.append(
                {
                    "document_id": record.document_id,
                    "title": record.title,
                    "summary": record.summary,
                    "matched_terms": matched_terms,
                    "match_score": len(matched_terms),
                }
            )

        ranked_matches.sort(key=lambda match: match["match_score"], reverse=True)
        return ranked_matches[:limit]

    def search(
        self,
        query_text: str,
        limit: int = 3,
    ) -> dict[str, object]:
        top_matches = self.preview_matches(query_text=query_text, limit=limit)
        return {
            "query": query_text,
            "total_matches": len(top_matches),
            "matches": top_matches,
        }
