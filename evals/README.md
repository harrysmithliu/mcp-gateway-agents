# Agent Evaluation

The `evals/` package is an independent, deterministic evaluation boundary for
tool planning, authorization, retrieval status, and citation contracts.

Run the versioned core dataset without a paid model API:

```bash
uv run --env-file .env --no-sync python scripts/run_agent_evaluation.py
```

The command writes a JSON report to `artifacts/evaluations/core_v1.json`.
Reports are local artifacts and are intentionally excluded from Git.

The in-process target is the default CI baseline. Set
`EMBEDDING_LOCAL_FILES_ONLY=true` after the model has been cached to avoid
runtime network checks. Keep it `false` on a fresh machine so the first run can
download the model. A failed case is a real contract failure unless the report
identifies an unavailable runtime, such as a missing local model or unavailable
PostgreSQL/pgvector service.
