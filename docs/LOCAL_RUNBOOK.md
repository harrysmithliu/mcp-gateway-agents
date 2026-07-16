# Local Runbook

This runbook is the shortest supported path for another developer to pull the repository, start the local runtime, seed the platform-owned state, and verify the authenticated product workflow with real PostgreSQL and Redis services.

## Prerequisites

- Python 3.11+
- Docker Desktop or another local Docker runtime with Compose support, already running
- an activated virtual environment
- project dependencies installed from `pyproject.toml`

## 1. Prepare Environment

```bash
cp .env.example .env
python3 -m pip install -e .
```

Default local values already point to:

- PostgreSQL: `postgresql://postgres:postgres@localhost:5432/mcp_gateway_agents`
- Redis: `redis://localhost:6379/0`
- FastAPI: `http://127.0.0.1:8000`
- Streamlit: `http://127.0.0.1:8501`

## 2. Start PostgreSQL And Redis

```bash
docker compose up -d postgres redis
```

Wait until both containers are healthy.

If `docker compose` reports that it cannot connect to the Docker daemon, start Docker Desktop first and rerun the command.

## 3. Apply Migrations And Seed Core State

```bash
python3 scripts/bootstrap_local_state.py
python3 scripts/seed_demo_data.py
```

Expected outcome:

- all SQL migrations under `sql/migrations/` are applied
- core role seed under `sql/seeds/` is applied
- canonical demo datasets under `data/demo/` are validated and summarized

## 4. Start Application Services

Backend:

```bash
uvicorn backend.api.app:app --reload --port 8000
```

Frontend:

```bash
streamlit run frontend/app.py
```

## 5. Verify Service Availability

- API health: `http://127.0.0.1:8000/health`
- Streamlit shell: `http://127.0.0.1:8501`

The frontend should show:

- active role selector
- current chat session indicator
- reset chat session button
- chat form and tool debug panel
- Account Investigation, Risk Scoring, Alerts, and Audit Review pages

## 6. Run End-To-End Verification

With the backend running:

```bash
python3 scripts/verify_local_e2e.py
```

The verification script uses the frontend HTTP client seam to call `/chat`, then confirms:

- a persisted `convo.chat_sessions` row exists
- persisted `convo.chat_messages` rows exist
- persisted `audit.tool_call_logs` rows exist
- persisted `audit.audit_events` rows exist
- a persisted `risk.risk_alerts` row exists
- Redis short-term context contains the chat session messages

The script prints a JSON report with the `session_id`, selected tool names, Redis message count, and PostgreSQL persistence counts.

For the authenticated analyst-to-risk-operator-to-supervisor workflow, run:

```bash
uv run --env-file .env --no-sync python scripts/verify_round7_workflow.py
```

This verifies account investigation access, risk batch scoring, risk-operator alert acknowledgement, supervisor approval, audit review, and the corresponding analyst denials. It prints role and status metadata only; bearer tokens are never printed.

For the offline Batch 6 closure checks, run:

```bash
uv run --no-sync python scripts/verify_batch6_closure.py
```

This verifies cache hit/miss and Redis-unavailable fallback, bounded planner memory, pre-invocation action blocking, evidence downgrade, and the versioned deterministic evaluation dataset without calling a paid LLM API.

## 7. Manual Demo Flow

Open Streamlit and use the default chat prompt or a richer one such as:

```text
Please search the policy playbook, score this borrower account, review the trade wallet volume gamma, and create an alert for this suspicious risk review.
```

Expected manual results:

- the frontend displays a returned `session_id`
- planned tool calls and tool invocation results are visible
- evidence notes and recommended actions are rendered
- sending a second message continues the same session unless `Reset Chat Session` is clicked

## 8. Troubleshooting

- If `bootstrap_local_state.py` fails, verify PostgreSQL is up on port `5432`.
- If `verify_local_e2e.py` cannot reach the API, verify `uvicorn` is running on port `8000`.
- If Redis validation fails, verify the Redis container is up on port `6379`.
- If the frontend cannot talk to the backend, verify both services use the same local host and port values from `.env`.
