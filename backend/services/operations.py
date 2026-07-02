from dataclasses import dataclass


@dataclass(slots=True)
class OperationsService:
    """Placeholder for alerts, case actions, and audit workflows."""

    service_name: str = "operations"

    def describe(self) -> str:
        return (
            "Placeholder operations service. "
            "Alert handling, case actions, and audit workflow helpers will be added later."
        )
