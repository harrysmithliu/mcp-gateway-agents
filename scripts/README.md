# Scripts

These commands support local setup, state management, diagnostics, deterministic verification, and explicit provider smoke tests. Run them from the repository root.

## Setup And Data

- `uv run --env-file .env --no-sync python scripts/bootstrap_local_state.py` applies SQL migrations and seeds in deterministic filename order. It writes only to the configured project-owned PostgreSQL runtime.
- `uv run --env-file .env --no-sync python scripts/seed_demo_data.py` validates canonical local trade, risk, knowledge, and operations datasets. It does not call a paid model.

## Local State

- `uv run --env-file .env --no-sync python scripts/reset_local_state.py --scope runtime` prints a redacted dry-run reset plan. Add `--confirm` only for an intentional local runtime reset.
- `uv run --env-file .env --no-sync python scripts/reset_local_state.py --scope demo` includes project-owned knowledge, identities, and demo records. It never drops the database, deletes Docker volumes, or touches external resources.

## Readiness And Delivery

- `uv run --no-sync python scripts/doctor_local_runtime.py --require-frontend` performs read-only backend and frontend reachability checks and prints a stable JSON report.
- `uv run --no-sync python scripts/verify_delivery.py --list-stages` prints the available verification stages, dependencies, runtime requirements, local-state mutation markers, and paid-provider boundaries.
- `uv run --no-sync python scripts/verify_delivery.py --profile offline` runs deterministic cache, memory, guardrail, evidence, and evaluation checks without PostgreSQL, Redis, model download, or a paid API.
- `uv run --env-file .env --no-sync python scripts/verify_delivery.py --profile local` runs readiness, data, RAG/MCP, authenticated workflow, cache/guardrail, and deterministic evaluation checks against the local runtime. Some stages write project-owned local records.
- `uv run --env-file .env --no-sync python scripts/verify_batch7_delivery.py --mode inspect` runs the read-only readiness handoff check.
- `uv run --env-file .env --no-sync python scripts/verify_batch7_delivery.py --mode verify_current --allow-local-writes` runs the local delivery handoff against the current project-owned state.
- `uv run --env-file .env --no-sync python scripts/verify_batch7_delivery.py --mode reset_and_verify --allow-local-writes --confirm-reset` explicitly resets demo state, then runs the local delivery handoff.

## Domain Verification

- `uv run --env-file .env --no-sync python scripts/verify_local_e2e.py` verifies two-turn chat persistence across PostgreSQL and Redis, including sessions, messages, tool logs, audit events, and short-term context. The blocked high-impact action must not create an operational alert record.
- `uv run --env-file .env --no-sync python scripts/verify_knowledge_ingestion.py` applies the local SQL plan, ingests the default knowledge sources into PostgreSQL/pgvector, and reports persisted documents, chunks, and embeddings.
- `uv run --env-file .env --no-sync python scripts/verify_round7_workflow.py` verifies analyst, risk operator, and supervisor account investigation, scoring, alert acknowledgement, approval, audit, and authorization behavior.
- `uv run --env-file .env --no-sync python scripts/verify_round4_ingestion.py` verifies admin-only knowledge refresh, source manifest, persisted RAG counts, and the success audit event.
- `uv run --env-file .env --no-sync python scripts/verify_round5_refresh.py` verifies repeatable knowledge refresh, unchanged-source no-op behavior, referential integrity, and vector dimensions.
- `uv run --env-file .env --no-sync python scripts/verify_round6_mcp_retrieval.py` verifies server-owned access scopes, HTTP/Agent/MCP retrieval parity, citations, and disabled retrieval behavior.
- `uv run --env-file .env --no-sync python scripts/verify_round8_evidence_layer.py` verifies Compose readiness, idempotent SQL bootstrap, controlled knowledge persistence, admin refresh, retrieval parity, citations, and disabled retrieval closure.
- `uv run --env-file .env --no-sync python scripts/verify_round5_persistence.py` verifies risk score persistence, alert status transition, and audit history.
- `uv run --no-sync python scripts/verify_mcp_transport.py` verifies one local SDK stdio `knowledge.search` call. Set `MCP_SERVER_RUNTIME=runtime` when the configured retrieval runtime is required. The four-tool SDK discovery and parity regression command is documented in `docs/LOCAL_RUNBOOK.md`.

## Evaluation

- `uv run --env-file .env --no-sync python scripts/run_agent_evaluation.py` runs the versioned deterministic agent evaluation dataset and writes a machine-readable report under `artifacts/evaluations/`.
- `uv run --no-sync python scripts/verify_batch6_closure.py` runs the offline cache, fallback, memory, guardrail, evidence, and deterministic evaluation closure without a paid model.

## Optional Paid Provider

- `uv run --env-file .env --no-sync python scripts/verify_anthropic_planner.py` performs exactly one live Anthropic structured-planner request. It requires `ANTHROPIC_API_KEY`, makes one provider call, and is never part of the default offline or local delivery profiles.
- `uv run --env-file .env --no-sync python scripts/verify_delivery.py --stage anthropic_planner --allow-paid-provider` explicitly selects the same paid-provider boundary through the delivery pipeline.

## Operational Rules

- Read the command description before running a state-mutating verifier.
- Keep `.env` local and never commit it.
- Use the offline profile for no-infrastructure, no-download, no-cost regression checks.
- Use the local profile only when Docker services and the project-owned local state are available.
- Use `inspect` when only runtime evidence is needed; use `verify_current` or `reset_and_verify` only with explicit local-write intent.
- Treat any paid-provider command as an explicit, separately budgeted smoke test.
