from dataclasses import dataclass

from backend.services.common import tokenize_text


@dataclass(frozen=True, slots=True)
class KnowledgeRecord:
    document_id: str
    title: str
    summary: str
    keywords: tuple[str, ...]


DEFAULT_KNOWLEDGE_RECORDS = (
    KnowledgeRecord(
        document_id="playbook-trade-risk-review",
        title="Trade Risk Review Playbook",
        summary="Review wallet exposure, abnormal fills, and concentration changes before raising an alert.",
        keywords=("trade", "risk", "review", "wallet", "alert", "exposure"),
    ),
    KnowledgeRecord(
        document_id="runbook-ops-alert-triage",
        title="Operations Alert Triage Runbook",
        summary="Create follow-up actions only after confirming alert severity, owner, and evidence links.",
        keywords=("operations", "alert", "action", "triage", "owner", "evidence"),
    ),
    KnowledgeRecord(
        document_id="guide-knowledge-evidence",
        title="Knowledge Evidence Response Guide",
        summary="Return short evidence snippets with titles and matched terms so analysts can verify the reasoning path.",
        keywords=("knowledge", "search", "evidence", "analyst", "response", "matched"),
    ),
    KnowledgeRecord(
        document_id="policy-risk-escalation",
        title="Risk Escalation Policy",
        summary="Escalate high-risk trade reviews when exposure and suspicious activity indicators appear together.",
        keywords=("risk", "escalate", "trade", "exposure", "suspicious", "activity"),
    ),
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
