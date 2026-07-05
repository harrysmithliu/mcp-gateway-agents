from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class MCPToolDefinition:
    """Minimal MCP tool metadata for the current runnable loop."""

    name: str
    domain: str
    description: str


@dataclass(slots=True)
class ToolInvocationResult:
    """Result envelope for the registry-driven tool invocation seam."""

    tool_name: str
    domain: str
    invocation_status: str
    request_payload: dict[str, object] = field(default_factory=dict)
    response_payload: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class KnowledgeRecord:
    """Minimal internal knowledge record for the first runnable search flow."""

    document_id: str
    title: str
    summary: str
    keywords: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TradeMetricsSnapshot:
    """Minimal trade metrics snapshot for the first runnable analytics flow."""

    snapshot_id: str
    account_label: str
    wallet_id: str
    order_count_24h: int
    filled_notional_usd_24h: int
    net_exposure_usd: int
    concentration_ratio: float
    anomaly_flags: tuple[str, ...]
    keywords: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RiskAccountProfile:
    """Minimal risk profile for the first runnable account scoring flow."""

    profile_id: str
    account_label: str
    account_id: str
    risk_score: int
    risk_level: str
    review_status: str
    exposure_usd: int
    alert_count_30d: int
    risk_flags: tuple[str, ...]
    keywords: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OpsActionTemplate:
    """Minimal operations action template for the first runnable alert flow."""

    template_id: str
    action_type: str
    severity: str
    owner_team: str
    summary_template: str
    required_fields: tuple[str, ...]
    keywords: tuple[str, ...]


DEFAULT_MCP_TOOL_DEFINITIONS = (
    MCPToolDefinition(
        name="knowledge.search",
        domain="knowledge",
        description="Search internal knowledge and return evidence candidates.",
    ),
    MCPToolDefinition(
        name="risk.score_account",
        domain="risk",
        description="Score a single account for risk review.",
    ),
    MCPToolDefinition(
        name="trade.query_metrics",
        domain="trade",
        description="Retrieve trade and wallet metrics for analysis.",
    ),
    MCPToolDefinition(
        name="ops.create_alert_or_action",
        domain="operations",
        description="Prepare an alert or follow-up action payload.",
    ),
)


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


DEFAULT_TRADE_METRICS_SNAPSHOTS = (
    TradeMetricsSnapshot(
        snapshot_id="trade-snapshot-alpha",
        account_label="Alpha Market Maker",
        wallet_id="wallet-alpha-01",
        order_count_24h=184,
        filled_notional_usd_24h=2450000,
        net_exposure_usd=320000,
        concentration_ratio=0.41,
        anomaly_flags=("exposure_shift",),
        keywords=("trade", "wallet", "volume", "market", "maker", "alpha"),
    ),
    TradeMetricsSnapshot(
        snapshot_id="trade-snapshot-beta",
        account_label="Beta Treasury Wallet",
        wallet_id="wallet-beta-17",
        order_count_24h=42,
        filled_notional_usd_24h=780000,
        net_exposure_usd=110000,
        concentration_ratio=0.28,
        anomaly_flags=("none",),
        keywords=("trade", "wallet", "treasury", "beta", "exposure"),
    ),
    TradeMetricsSnapshot(
        snapshot_id="trade-snapshot-gamma",
        account_label="Gamma High-Volume Desk",
        wallet_id="wallet-gamma-88",
        order_count_24h=267,
        filled_notional_usd_24h=3910000,
        net_exposure_usd=540000,
        concentration_ratio=0.57,
        anomaly_flags=("volume_spike", "concentration_risk"),
        keywords=("trade", "wallet", "order", "volume", "gamma", "desk"),
    ),
)


DEFAULT_RISK_ACCOUNT_PROFILES = (
    RiskAccountProfile(
        profile_id="risk-profile-atlas",
        account_label="Atlas Prime Borrower",
        account_id="acct-atlas-01",
        risk_score=82,
        risk_level="high",
        review_status="escalate",
        exposure_usd=460000,
        alert_count_30d=4,
        risk_flags=("exposure_growth", "alert_recurrence"),
        keywords=("risk", "account", "borrower", "atlas", "prime", "score"),
    ),
    RiskAccountProfile(
        profile_id="risk-profile-beacon",
        account_label="Beacon Treasury Account",
        account_id="acct-beacon-17",
        risk_score=58,
        risk_level="medium",
        review_status="monitor",
        exposure_usd=190000,
        alert_count_30d=1,
        risk_flags=("concentration_watch",),
        keywords=("risk", "account", "treasury", "beacon", "score", "review"),
    ),
    RiskAccountProfile(
        profile_id="risk-profile-cobalt",
        account_label="Cobalt Growth Borrower",
        account_id="acct-cobalt-33",
        risk_score=31,
        risk_level="low",
        review_status="clear",
        exposure_usd=72000,
        alert_count_30d=0,
        risk_flags=("none",),
        keywords=("risk", "borrower", "account", "cobalt", "growth", "score"),
    ),
)


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
class ToolRegistry:
    """Minimal registry placeholder for later MCP tool wiring."""

    tools: dict[str, MCPToolDefinition] = field(default_factory=dict)

    def register(self, tool_definition: MCPToolDefinition) -> None:
        self.tools[tool_definition.name] = tool_definition

    def has_tool(self, tool_name: str) -> bool:
        return tool_name in self.tools

    def get_tool(self, tool_name: str) -> MCPToolDefinition | None:
        return self.tools.get(tool_name)

    def list_tool_names(self) -> list[str]:
        return list(self.tools)

    def invoke(
        self,
        tool_name: str,
        request_payload: dict[str, object] | None = None,
    ) -> ToolInvocationResult:
        tool_definition = self.get_tool(tool_name)
        if tool_definition is None:
            raise ValueError(f"Tool is not registered: {tool_name}")

        normalized_payload = request_payload or {}
        if tool_definition.name == "knowledge.search":
            return self._invoke_knowledge_search(tool_definition, normalized_payload)
        if tool_definition.name == "risk.score_account":
            return self._invoke_risk_score_account(tool_definition, normalized_payload)
        if tool_definition.name == "trade.query_metrics":
            return self._invoke_trade_query_metrics(tool_definition, normalized_payload)
        if tool_definition.name == "ops.create_alert_or_action":
            return self._invoke_ops_create_alert_or_action(
                tool_definition,
                normalized_payload,
            )

        return self._build_stub_result(tool_definition, normalized_payload)

    def _build_stub_result(
        self,
        tool_definition: MCPToolDefinition,
        request_payload: dict[str, object],
    ) -> ToolInvocationResult:
        response_payload = {
            "message": f"Stub invocation completed for {tool_definition.name}.",
            "description": tool_definition.description,
        }

        return ToolInvocationResult(
            tool_name=tool_definition.name,
            domain=tool_definition.domain,
            invocation_status="stubbed",
            request_payload=request_payload,
            response_payload=response_payload,
        )

    def _invoke_knowledge_search(
        self,
        tool_definition: MCPToolDefinition,
        request_payload: dict[str, object],
    ) -> ToolInvocationResult:
        query_text = self._extract_query_text(request_payload)
        top_matches = self.preview_knowledge_matches(query_text=query_text, limit=3)

        response_payload = {
            "query": query_text,
            "total_matches": len(top_matches),
            "matches": top_matches,
        }

        return ToolInvocationResult(
            tool_name=tool_definition.name,
            domain=tool_definition.domain,
            invocation_status="completed",
            request_payload=request_payload,
            response_payload=response_payload,
        )

    def preview_knowledge_matches(
        self,
        query_text: str,
        limit: int = 3,
    ) -> list[dict[str, object]]:
        query_terms = self._tokenize_text(query_text)

        ranked_matches = []
        for record in DEFAULT_KNOWLEDGE_RECORDS:
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

    def _extract_query_text(self, request_payload: dict[str, object]) -> str:
        raw_query = request_payload.get("query")
        if isinstance(raw_query, str) and raw_query.strip():
            return raw_query.strip()

        raw_message_text = request_payload.get("message_text")
        if isinstance(raw_message_text, str) and raw_message_text.strip():
            return raw_message_text.strip()

        return ""

    def _invoke_trade_query_metrics(
        self,
        tool_definition: MCPToolDefinition,
        request_payload: dict[str, object],
    ) -> ToolInvocationResult:
        query_text = self._extract_query_text(request_payload)
        query_terms = self._tokenize_text(query_text)

        ranked_snapshots = []
        for snapshot in DEFAULT_TRADE_METRICS_SNAPSHOTS:
            matched_terms = sorted(query_terms.intersection(snapshot.keywords))
            if not matched_terms:
                continue

            ranked_snapshots.append(
                {
                    "snapshot_id": snapshot.snapshot_id,
                    "account_label": snapshot.account_label,
                    "wallet_id": snapshot.wallet_id,
                    "order_count_24h": snapshot.order_count_24h,
                    "filled_notional_usd_24h": snapshot.filled_notional_usd_24h,
                    "net_exposure_usd": snapshot.net_exposure_usd,
                    "concentration_ratio": snapshot.concentration_ratio,
                    "anomaly_flags": list(snapshot.anomaly_flags),
                    "matched_terms": matched_terms,
                    "match_score": len(matched_terms),
                }
            )

        ranked_snapshots.sort(
            key=lambda snapshot: (
                snapshot["match_score"],
                snapshot["filled_notional_usd_24h"],
            ),
            reverse=True,
        )
        top_snapshots = ranked_snapshots[:3]

        total_filled_notional_usd_24h = sum(
            snapshot["filled_notional_usd_24h"] for snapshot in top_snapshots
        )
        max_concentration_ratio = max(
            (snapshot["concentration_ratio"] for snapshot in top_snapshots),
            default=0.0,
        )

        response_payload = {
            "query": query_text,
            "total_matches": len(top_snapshots),
            "total_filled_notional_usd_24h": total_filled_notional_usd_24h,
            "max_concentration_ratio": max_concentration_ratio,
            "snapshots": top_snapshots,
        }

        return ToolInvocationResult(
            tool_name=tool_definition.name,
            domain=tool_definition.domain,
            invocation_status="completed",
            request_payload=request_payload,
            response_payload=response_payload,
        )

    def _invoke_risk_score_account(
        self,
        tool_definition: MCPToolDefinition,
        request_payload: dict[str, object],
    ) -> ToolInvocationResult:
        query_text = self._extract_query_text(request_payload)
        query_terms = self._tokenize_text(query_text)

        ranked_profiles = []
        for profile in DEFAULT_RISK_ACCOUNT_PROFILES:
            matched_terms = sorted(query_terms.intersection(profile.keywords))
            if not matched_terms:
                continue

            ranked_profiles.append(
                {
                    "profile_id": profile.profile_id,
                    "account_label": profile.account_label,
                    "account_id": profile.account_id,
                    "risk_score": profile.risk_score,
                    "risk_level": profile.risk_level,
                    "review_status": profile.review_status,
                    "exposure_usd": profile.exposure_usd,
                    "alert_count_30d": profile.alert_count_30d,
                    "risk_flags": list(profile.risk_flags),
                    "matched_terms": matched_terms,
                    "match_score": len(matched_terms),
                }
            )

        ranked_profiles.sort(
            key=lambda profile: (
                profile["match_score"],
                profile["risk_score"],
                profile["exposure_usd"],
            ),
            reverse=True,
        )
        top_profiles = ranked_profiles[:3]

        highest_risk_score = max(
            (profile["risk_score"] for profile in top_profiles),
            default=0,
        )
        max_exposure_usd = max(
            (profile["exposure_usd"] for profile in top_profiles),
            default=0,
        )

        response_payload = {
            "query": query_text,
            "total_matches": len(top_profiles),
            "highest_risk_score": highest_risk_score,
            "max_exposure_usd": max_exposure_usd,
            "profiles": top_profiles,
        }

        return ToolInvocationResult(
            tool_name=tool_definition.name,
            domain=tool_definition.domain,
            invocation_status="completed",
            request_payload=request_payload,
            response_payload=response_payload,
        )

    def _invoke_ops_create_alert_or_action(
        self,
        tool_definition: MCPToolDefinition,
        request_payload: dict[str, object],
    ) -> ToolInvocationResult:
        query_text = self._extract_query_text(request_payload)
        query_terms = self._tokenize_text(query_text)

        ranked_templates = []
        for template in DEFAULT_OPS_ACTION_TEMPLATES:
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
        top_templates = ranked_templates[:3]

        recommended_action = top_templates[0] if top_templates else None

        response_payload = {
            "query": query_text,
            "total_matches": len(top_templates),
            "recommended_action": recommended_action,
            "templates": top_templates,
        }

        return ToolInvocationResult(
            tool_name=tool_definition.name,
            domain=tool_definition.domain,
            invocation_status="completed",
            request_payload=request_payload,
            response_payload=response_payload,
        )

    def _tokenize_text(self, text: str) -> set[str]:
        normalized_text = text.lower()
        tokens = {
            token.strip(".,!?():;[]{}")
            for token in normalized_text.split()
            if token.strip(".,!?():;[]{}")
        }
        return tokens


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for tool_definition in DEFAULT_MCP_TOOL_DEFINITIONS:
        registry.register(tool_definition)
    return registry
