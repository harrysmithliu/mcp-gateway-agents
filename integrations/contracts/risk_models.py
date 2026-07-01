from dataclasses import dataclass


@dataclass(slots=True)
class RiskScoreResult:
    account_id: str
    risk_probability: float
    risk_band: str
    threshold_label: str

