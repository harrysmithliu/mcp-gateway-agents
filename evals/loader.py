from __future__ import annotations

import json
from pathlib import Path

from evals.contracts import EvalCase


def load_eval_cases(path: str | Path) -> tuple[EvalCase, ...]:
    """Load and validate newline-delimited evaluation cases."""

    dataset_path = Path(path)
    cases: list[EvalCase] = []
    seen_case_ids: set[str] = set()
    for line_number, raw_line in enumerate(
        dataset_path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid evaluation JSON at line {line_number}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"evaluation case at line {line_number} must be an object")
        case = EvalCase.from_mapping(payload)
        if case.case_id in seen_case_ids:
            raise ValueError(f"duplicate evaluation case id: {case.case_id}")
        seen_case_ids.add(case.case_id)
        cases.append(case)
    if not cases:
        raise ValueError(f"evaluation dataset is empty: {dataset_path}")
    return tuple(cases)
