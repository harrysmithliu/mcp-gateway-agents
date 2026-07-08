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
