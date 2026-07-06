from dataclasses import dataclass

from backend.services.common import tokenize_text
from backend.services.demo_data import load_demo_dataset


@dataclass(frozen=True, slots=True)
class OpsActionTemplate:
    template_id: str
    action_type: str
    severity: str
    owner_team: str
    summary_template: str
    required_fields: tuple[str, ...]
    keywords: tuple[str, ...]


DEFAULT_OPS_ACTION_TEMPLATES = tuple(
    OpsActionTemplate(
        template_id=str(record["template_id"]),
        action_type=str(record["action_type"]),
        severity=str(record["severity"]),
        owner_team=str(record["owner_team"]),
        summary_template=str(record["summary_template"]),
        required_fields=tuple(str(field_name) for field_name in record["required_fields"]),
        keywords=tuple(str(keyword) for keyword in record["keywords"]),
    )
    for record in load_demo_dataset("operations")
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
