# Scripts

This directory contains setup, seeding, indexing, and utility scripts.

## Available Scripts

- `python3 scripts/seed_demo_data.py`
  Validates the canonical demo datasets under `data/demo/` and prints a JSON summary with dataset paths and record counts for local trade, risk, knowledge, and operations demos.
- `python3 scripts/bootstrap_local_state.py`
  Applies local SQL migrations and seed files to the configured PostgreSQL database in deterministic filename order.
- `uv run --env-file .env --no-sync python scripts/reset_local_state.py --scope runtime`
  Prints a redacted dry-run plan by default. Add `--confirm` only when the local runtime state should be cleared; use `--scope demo` to also clear knowledge and reseed demo identities.
- `uv run --no-sync python scripts/doctor_local_runtime.py`
  Runs read-only backend readiness and frontend reachability checks and prints a stable JSON report. Add `--require-frontend` when both local services are required; this command never starts, migrates, seeds, resets, or downloads a model.
- `uv run --no-sync python scripts/verify_delivery.py --list-stages`
  Lists the delivery verification stages, dependencies, runtime requirements, local-state mutation markers, and paid-provider boundaries.
- `uv run --no-sync python scripts/verify_delivery.py --profile offline`
  Runs the cache/guardrail closure, including its deterministic `core_v1` assertions, without requiring PostgreSQL, Redis, frontend, embedding downloads, or an Anthropic API key.
- `uv run --env-file .env --no-sync python scripts/verify_delivery.py --profile local`
  Runs readiness, knowledge evidence state, RAG/MCP parity, authenticated workflows, cache/guardrail closure, and deterministic evaluation against the local Compose runtime. The data-state and workflow stages may write project-owned local records.
- `uv run --env-file .env --no-sync python scripts/verify_delivery.py --stage anthropic_planner --allow-paid-provider`
  Explicitly opts into exactly one Anthropic planner smoke request; it is excluded from every default profile and delivery check.
- `python3 scripts/verify_knowledge_ingestion.py`
  Applies the local SQL plan, ingests the default knowledge source set into PostgreSQL/pgvector, and prints a JSON report that verifies persisted documents, chunks, and embeddings.
- `python3 scripts/verify_local_e2e.py`
  Uses the frontend HTTP client seam against a live local backend, then checks PostgreSQL and user-scoped Redis to verify a real persisted chat session, messages, tool logs, audit events, and a blocked high-impact action without creating an operational alert record.
- `uv run --env-file .env --no-sync python scripts/verify_anthropic_planner.py`
  Performs exactly one live Anthropic structured-planner request and prints only safe planner metadata; it does not retry or use the legacy fallback path.
- `uv run --no-sync python scripts/verify_mcp_transport.py`
  Runs one local `sdk_stdio` knowledge tool call and prints safe transport and canonical knowledge metadata; set `MCP_SERVER_RUNTIME=runtime` to use the configured retrieval runtime.
- `uv run --env-file .env --no-sync python scripts/verify_round6_mcp_retrieval.py`
  Verifies server-owned analyst/admin access scopes, canonical HTTP/Agent/MCP retrieval semantics, citation stability and the disabled retrieval contract without calling a paid LLM API.
- `uv run --env-file .env --no-sync python scripts/verify_round8_evidence_layer.py`
  Verifies Compose readiness, idempotent SQL bootstrap, controlled knowledge persistence, admin refresh, analyst citations, HTTP/Agent/MCP retrieval parity and disabled retrieval closure without calling a paid LLM API.
- `uv run --env-file .env --no-sync python scripts/run_agent_evaluation.py`
  Runs the versioned deterministic Agent evaluation dataset through the in-process target and writes a machine-readable report under `artifacts/evaluations/`.
- `uv run --no-sync python scripts/verify_batch6_closure.py`
  Runs the offline Batch 6 closure verifier for cache hit/miss and Redis fallback, bounded memory, pre-invocation action blocking, evidence downgrade, and the versioned deterministic evaluation dataset without a paid LLM API.
- `uv run --env-file .env --no-sync python scripts/verify_round5_persistence.py`
  Applies local migrations, writes and reads a risk batch score, transitions a risk alert, and verifies its audit history.
- `uv run --env-file .env --no-sync python scripts/verify_round7_workflow.py`
  Verifies authenticated analyst, risk operator, and supervisor workflows, including account investigation access, risk scoring, alert acknowledgement, approval decision, and audit authorization.
- `uv run --env-file .env --no-sync python scripts/verify_round4_ingestion.py`
  Applies local migrations, verifies admin-only knowledge refresh, checks source manifest and persisted RAG counts, and confirms the success audit event.
- `uv run --env-file .env --no-sync python scripts/verify_round5_refresh.py`
  Verifies repeatable knowledge refresh, no-op behavior on unchanged sources, and PostgreSQL/pgvector referential and vector-dimension integrity.
