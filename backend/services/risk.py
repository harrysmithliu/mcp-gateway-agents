from dataclasses import dataclass

from backend.services.common import tokenize_text


@dataclass(frozen=True, slots=True)
class RiskAccountProfile:
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


@dataclass(slots=True)
class RiskService:
    profiles: tuple[RiskAccountProfile, ...] = DEFAULT_RISK_ACCOUNT_PROFILES

    def score_account(
        self,
        query_text: str,
        limit: int = 3,
    ) -> dict[str, object]:
        query_terms = tokenize_text(query_text)
        ranked_profiles = []

        for profile in self.profiles:
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
        top_profiles = ranked_profiles[:limit]

        return {
            "query": query_text,
            "total_matches": len(top_profiles),
            "highest_risk_score": max(
                (profile["risk_score"] for profile in top_profiles),
                default=0,
            ),
            "max_exposure_usd": max(
                (profile["exposure_usd"] for profile in top_profiles),
                default=0,
            ),
            "profiles": top_profiles,
        }
