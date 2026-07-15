from typing import Protocol

from evals.contracts import EvalCase, EvalObservation


class EvaluationTarget(Protocol):
    """Adapter boundary for in-process, HTTP, or future target implementations."""

    def evaluate(self, case: EvalCase) -> EvalObservation: ...
