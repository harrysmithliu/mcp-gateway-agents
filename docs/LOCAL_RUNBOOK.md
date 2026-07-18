# Local Runbook

This runbook is the supported local path for starting the authenticated platform with project-owned PostgreSQL/pgvector, Redis, FastAPI, and Streamlit services.

## Prerequisites

- Python 3.11 or newer
- `uv` for locked local dependency installation
- Docker Desktop or another Docker Compose runtime, already running
- access to the repository directory

The default local workflow does not require an Anthropic API key. Compose reuses the host Hugging Face cache at `${HOME}/.cache/huggingface`, so a cached local embedding model is available inside the backend container without committing model files. If the model is not cached, the first local run may download it into that host cache.

## 1. Prepare Environment

```bash
cp .env.example .env
```

For local JWT authentication, replace `AUTH_JWT_SECRET` in `.env` with a random local value. Keep `ANTHROPIC_API_KEY` blank unless the explicit paid planner smoke is being run.

Install the locked dependencies once:

```bash
uv sync --dev
```

## 2. Start The Local Stack

The recommended path builds and starts all four services. Backend startup applies the project SQL plan, including migrations and seeds, before serving FastAPI.

```bash
docker compose up -d --build
docker compose ps
```

Expected services:

- PostgreSQL/pgvector: `localhost:5432`
- Redis: `localhost:6379`
- FastAPI: `http://127.0.0.1:8000`
- Streamlit: `http://127.0.0.1:8501`

## 3. Verify The First Startup

```bash
curl http://127.0.0.1:8000/health
uv run --no-sync python scripts/doctor_local_runtime.py --require-frontend
```

The health payload reports retrieval and component readiness. The doctor command is read-only and reports actionable degraded/unavailable states without printing credentials.

## 4. Sign In Through The Application

Open `http://127.0.0.1:8501/`. Sign in from the Home page sidebar using one of the seeded local demo users:

- `analyst_demo` for evidence and investigation flows
- `risk_operator_demo` for scoring and alert acknowledgement
- `supervisor_demo` for approval and audit review
- `admin_demo` for knowledge administration and System Status

The local seed uses `demo-password` for these demo identities. Change or replace this local-only seed before any non-demo deployment.

The admin-only `System Status` page exposes readiness, migration, runtime mode, and MCP visibility as a read-only, redacted operational view.

## 5. Optional Host-Process Path

Use this path when PostgreSQL and Redis are already running separately and the application processes should run on the host:

```bash
docker compose up -d postgres redis
uv run --env-file .env --no-sync python scripts/bootstrap_local_state.py
uv run --env-file .env --no-sync streamlit run frontend/app.py
uv run --env-file .env --no-sync uvicorn backend.api.app:app --reload --port 8000
```

Run the backend and frontend commands in separate terminals. When using Compose for the application services, do not start a second host process on ports `8000` or `8501`.

## 6. Safe Local Operations

When running application processes on the host, apply the SQL plan explicitly:

```bash
uv run --env-file .env --no-sync python scripts/bootstrap_local_state.py
uv run --env-file .env --no-sync python scripts/seed_demo_data.py
```

`bootstrap_local_state.py` is idempotent and records applied files in `public.local_sql_scripts`. `seed_demo_data.py` validates the canonical local demo datasets; it does not call a paid model.

Inspect reset effects before changing local state:

```bash
uv run --env-file .env --no-sync python scripts/reset_local_state.py --scope runtime
```

The reset command is dry-run by default. Only use `--confirm` after verifying the target is the project-owned local PostgreSQL/Redis runtime. Use `--scope demo` only when knowledge, identities, and demo records should also be rebuilt. The reset flow does not drop the database, delete Docker volumes, or touch external resources.

## 7. Verification Paths

Read-only runtime diagnosis:

```bash
uv run --no-sync python scripts/doctor_local_runtime.py --require-frontend
```

Offline verification with no PostgreSQL, Redis, model download, or paid API:

```bash
uv run --no-sync python scripts/verify_delivery.py --profile offline
```

Local Compose verification, including state-mutating workflow stages:

```bash
uv run --env-file .env --no-sync python scripts/verify_delivery.py --profile local
```

For one handoff report covering runtime readiness, data state, RAG/MCP, authenticated workflow, cache/guardrails, and deterministic evaluation, run:

```bash
uv run --env-file .env --no-sync python scripts/verify_batch7_delivery.py --mode inspect
uv run --env-file .env --no-sync python scripts/verify_batch7_delivery.py --mode verify_current --allow-local-writes
```

The `inspect` mode is read-only. The `verify_current` mode may write project-owned local records through the existing delivery stages. To verify a rebuilt demo baseline, use `reset_and_verify` only after reviewing the reset target and explicitly adding both `--allow-local-writes` and `--confirm-reset`.

The local chat persistence verifier checks sessions, messages, tool invocation logs, audit events, and Redis context. Its high-impact operations action is expected to be blocked before invocation; it must not create a `risk.risk_alerts` operational record.

The authenticated workflow verifier checks analyst, risk operator, and supervisor access, scoring, approval, and audit behavior. The paid Anthropic planner is never part of these default paths.

## 8. Manual Demo Flow

Open Streamlit and use the default chat prompt or a richer one such as:

```text
Please search the policy playbook, score this borrower account, review the trade wallet volume gamma, and create an alert for this suspicious risk review.
```

Expected manual results:

- the frontend displays a returned `session_id`
- planned tool calls and tool invocation results are visible
- evidence notes and recommended actions are rendered
- sending a second message continues the same session unless `Reset Chat Session` is clicked

## 9. Troubleshooting

- If Compose cannot connect to the Docker daemon, start Docker Desktop and rerun the command.
- If PostgreSQL or Redis is unavailable, check `docker compose ps` and verify ports `5432` and `6379`.
- If the API is unavailable, check `docker compose logs backend` or verify the host `uvicorn` process on port `8000`.
- If the frontend cannot reach the backend, use `API_BASE_URL=http://localhost:8000` for host execution; Compose supplies `http://backend:8000` inside the frontend container.
- If retrieval reports unavailable because the model is not cached, allow the first local model download or set `EMBEDDING_LOCAL_FILES_ONLY=true` to require an existing cache.
- If a rebuilt endpoint returns `404`, rebuild and recreate the backend/frontend images with `docker compose up -d --build backend frontend`.
- If the handoff report is blocked, inspect its `reason` before adding write or reset confirmation flags; a blocked report does not modify local state.
