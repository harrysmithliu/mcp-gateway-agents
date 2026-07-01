# mcp-gateway-agents

Phase 1 skeleton for an MCP gateway plus agentic crypto risk platform.

## Scope

This repository is the project-owned application layer that will combine:

- a Streamlit frontend
- a FastAPI backend
- an Anthropic-powered agent workflow
- an MCP gateway and tool registry
- local adapters to upstream trade-analysis and risk-model projects

The detailed target plan lives in [docs/PROJECT_REQUIREMENTS.md](docs/PROJECT_REQUIREMENTS.md).

## Phase 1 Deliverables

- repository skeleton aligned with the requirements document
- minimal backend health app
- minimal frontend shell with demo login / role switch entry
- environment template
- initial SQL migrations for core schemas and tables
- placeholder integration contracts and module boundaries

## Repository Layout

```text
mcp-gateway-agents/
├── backend/
├── data/
├── docs/
├── frontend/
├── integrations/
├── scripts/
├── sql/
└── tests/
```

## Quick Start

### 1. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
python3 -m pip install -e .
```

### 3. Copy environment variables

```bash
cp .env.example .env
```

### 4. Start the backend

```bash
uvicorn backend.api.app:app --reload --port 8000
```

Open `http://127.0.0.1:8000/health` to verify the API is running.

### 5. Start the frontend

```bash
streamlit run frontend/app.py
```

## Initial Data Layer

The first SQL migrations live under `sql/migrations/` and currently define:

- logical schemas for identity, conversation, trading, risk, knowledge, and audit data
- the first role, user, chat-session, chat-message, and audit-event tables

## Notes

- `texts/` is intentionally ignored and treated as scratch or raw ideation space.
- Upstream projects are not required to expose remote APIs in Phase 1.
- The current frontend shell uses a demo role-switch flow so RBAC can be exercised early.
