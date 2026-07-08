from pathlib import Path

from backend.retrieval.ingestion_models import KnowledgeSourceDocument


PROJECT_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_SOURCE_DIR = PROJECT_ROOT / "data" / "knowledge_sources"


DEFAULT_INGESTION_DOCUMENTS = (
    KnowledgeSourceDocument(
        source_id="kb-policy-trading-surveillance",
        title="Trading Surveillance Policy",
        file_path=str(
            KNOWLEDGE_SOURCE_DIR / "trading_surveillance_policy.md"
        ),
        content_type="text/markdown",
        tags=("policy", "trading", "surveillance"),
        jurisdiction="global",
        access_level="internal",
    ),
    KnowledgeSourceDocument(
        source_id="kb-risk-alert-handling",
        title="Risk Alert Handling Playbook",
        file_path=str(
            KNOWLEDGE_SOURCE_DIR / "risk_alert_handling_playbook.md"
        ),
        content_type="text/markdown",
        tags=("playbook", "risk", "operations"),
        jurisdiction="global",
        access_level="internal",
    ),
)