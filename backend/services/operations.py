from dataclasses import dataclass

from backend.services.common import tokenize_text


@dataclass(frozen=True, slots=True)
class OpsActionTemplate:
    template_id: str
    action_type: str
    severity: str
    owner_team: str
    summary_template: str
    required_fields: tuple[str, ...]
    keywords: tuple[str, ...]


DEFAULT_OPS_ACTION_TEMPLATES = (
    OpsActionTemplate(
        template_id="ops-alert-escalation",
        action_type="alert",
        severity="high",
        owner_team="risk_ops",
        summary_template="Escalate suspicious trading activity with exposure context and supporting evidence.",
        required_fields=("account_id", "exposure_context", "evidence_links"),
        keywords=("alert", "escalate", "suspicious", "risk", "review"),
    ),
    OpsActionTemplate(
        template_id="ops-review-followup",
        action_type="review",
        severity="medium",
        owner_team="trade_ops",
        summary_template="Prepare a manual review packet for abnormal trade metrics and concentration changes.",
        required_fields=("wallet_id", "metric_snapshot", "review_notes"),
        keywords=("review", "trade", "wallet", "metrics", "follow-up"),
    ),
    OpsActionTemplate(
        template_id="ops-action-monitor",
        action_type="action",
        severity="low",
        owner_team="operations_control",
        summary_template="Open a monitoring action to track repeated but lower-severity anomalies.",
        required_fields=("entity_id", "monitoring_window", "owner"),
        keywords=("action", "monitor", "operations", "owner", "triage"),
    ),
)


@dataclass(slots=True)
class OperationsService:
    """Operations helpers for alerts, case actions, and audit workflows."""

    service_name: str = "operations"
    templates: tuple[OpsActionTemplate, ...] = DEFAULT_OPS_ACTION_TEMPLATES

    def describe(self) -> str:
        return (
            "Placeholder operations service. "
            "Alert handling, case actions, and audit workflow helpers will be added later."
        )

    def create_alert_or_action(
        self,
        query_text: str,
        limit: int = 3,
    ) -> dict[str, object]:
        query_terms = tokenize_text(query_text)
        ranked_templates = []

        for template in self.templates:
            matched_terms = sorted(query_terms.intersection(template.keywords))
            if not matched_terms:
                continue

            ranked_templates.append(
                {
                    "template_id": template.template_id,
                    "action_type": template.action_type,
                    "severity": template.severity,
                    "owner_team": template.owner_team,
                    "summary_template": template.summary_template,
                    "required_fields": list(template.required_fields),
                    "matched_terms": matched_terms,
                    "match_score": len(matched_terms),
                }
            )

        ranked_templates.sort(
            key=lambda template: (
                template["match_score"],
                template["severity"] == "high",
                template["severity"] == "medium",
            ),
            reverse=True,
        )
        top_templates = ranked_templates[:limit]

        return {
            "query": query_text,
            "total_matches": len(top_templates),
            "recommended_action": top_templates[0] if top_templates else None,
            "templates": top_templates,
        }
