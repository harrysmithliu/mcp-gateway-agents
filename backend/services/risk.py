from dataclasses import dataclass

from backend.services.common import tokenize_text
from backend.services.demo_data import load_demo_dataset


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


DEFAULT_RISK_ACCOUNT_PROFILES = tuple(
    RiskAccountProfile(
        profile_id=str(record["profile_id"]),
        account_label=str(record["account_label"]),
        account_id=str(record["account_id"]),
        risk_score=int(record["risk_score"]),
        risk_level=str(record["risk_level"]),
        review_status=str(record["review_status"]),
        exposure_usd=int(record["exposure_usd"]),
        alert_count_30d=int(record["alert_count_30d"]),
        risk_flags=tuple(str(flag) for flag in record["risk_flags"]),
        keywords=tuple(str(keyword) for keyword in record["keywords"]),
    )
    for record in load_demo_dataset("risk")
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
