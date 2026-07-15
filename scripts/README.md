# Scripts

This directory contains setup, seeding, indexing, and utility scripts.

## Available Scripts

- `python3 scripts/seed_demo_data.py`
  Validates the canonical demo datasets under `data/demo/` and prints a JSON summary with dataset paths and record counts for local trade, risk, knowledge, and operations demos.
- `python3 scripts/bootstrap_local_state.py`
  Applies local SQL migrations and seed files to the configured PostgreSQL database in deterministic filename order.
- `python3 scripts/verify_knowledge_ingestion.py`
  Applies the local SQL plan, ingests the default knowledge source set into PostgreSQL/pgvector, and prints a JSON report that verifies persisted documents, chunks, and embeddings.
- `python3 scripts/verify_local_e2e.py`
  Uses the frontend HTTP client seam against a live local backend, then checks PostgreSQL and Redis to verify a real persisted chat session, messages, tool logs, audit events, and operational alert records.
- `uv run --env-file .env --no-sync python scripts/verify_anthropic_planner.py`
  Performs exactly one live Anthropic structured-planner request and prints only safe planner metadata; it does not retry or use the legacy fallback path.
- `uv run --no-sync python scripts/verify_mcp_transport.py`
  Runs one local `sdk_stdio` knowledge tool call and prints safe transport metadata; set `MCP_SERVER_RUNTIME=runtime` to use the configured retrieval runtime.
- `uv run --env-file .env --no-sync python scripts/verify_round5_persistence.py`
  Applies local migrations, writes and reads a risk batch score, transitions a risk alert, and verifies its audit history.
- `uv run --env-file .env --no-sync python scripts/verify_round7_workflow.py`
  Verifies authenticated analyst, risk operator, and supervisor workflows, including account investigation access, risk scoring, alert acknowledgement, approval decision, and audit authorization.
- `uv run --env-file .env --no-sync python scripts/verify_round4_ingestion.py`
  Applies local migrations, verifies admin-only knowledge refresh, checks source manifest and persisted RAG counts, and confirms the success audit event.
- `uv run --env-file .env --no-sync python scripts/verify_round5_refresh.py`
  Verifies repeatable knowledge refresh, no-op behavior on unchanged sources, and PostgreSQL/pgvector referential and vector-dimension integrity.
