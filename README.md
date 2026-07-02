# mcp-gateway-agents

AI agentic crypto risk operations platform with an MCP gateway, Streamlit frontend, FastAPI backend, LLM orchestration, retrieval, cache, and local adapters for trading analytics and risk scoring.

## Overview

This repository is the project-owned application layer for a crypto risk copilot. It brings together:

- a Streamlit frontend
- a FastAPI backend
- a LangChain-based agent workflow with Claude-compatible models
- an MCP gateway for tool orchestration
- retrieval over internal knowledge and operating rules
- Redis-backed cache and short-term conversation context
- local adapters to upstream trade-analysis and risk-model projects
- project-owned operational data, alerts, cases, and audit records

The detailed product requirements live in [docs/PROJECT_REQUIREMENTS.md](docs/PROJECT_REQUIREMENTS.md).

## What The Platform Does

The platform is designed for crypto trading risk operations workflows such as:

- investigating unusual account or wallet activity
- asking natural-language questions about suspicious trading behavior
- scoring accounts with a local risk model
- retrieving policy, model, and case knowledge with evidence
- creating alerts and review actions
- maintaining an audit trail for operator and agent activity

Representative prompts:

- `Which accounts became riskier in the last 24 hours?`
- `Why was this wallet flagged as suspicious?`
- `Show me top accounts by abnormal turnover and high model risk.`
- `Run batch risk scoring for accounts with repeated failed withdrawals.`

## Architecture

```mermaid
flowchart TD
    UI["Streamlit UI"] --> API["FastAPI Backend"]
    API --> RBAC["RBAC / Authorization"]
    API --> AGENT["Agent Engine"]

    AGENT --> REDIS["Redis Cache"]
    AGENT --> RAG["RAG Retrieval Layer"]
    AGENT --> MCP["MCP Gateway"]
    AGENT --> LLM["Claude-compatible LLM"]
    AGENT --> GUARD["Guardrails"]

    RAG --> DB["PostgreSQL + Vector Retrieval"]
    MCP --> TRADE["Trading Adapters"]
    MCP --> RISK["Risk Model Adapters"]
    MCP --> OPS["Alert / Case Tools"]
```

## Upstream Sources

This project reuses upstream assets as one-way sources rather than as user-facing applications:

- trade analytics source: `crypto_trade_plot`
  vendored path: `integrations/sources/trade_source/vendor/crypto_trade_plot/`
- risk scoring source: `ml_risk_control`
  vendored path: `integrations/sources/risk_source/vendor/ml_risk_control/`

The integration approach favors local adapters over mandatory upstream APIs so the platform can run locally as a single project-owned application.

## Core Capabilities

- unified frontend owned by this repository
- RBAC-aware workflow entry and operator views
- MCP-based tool calling for trade, risk, knowledge, and ops tasks
- retrieval-backed answers with supporting evidence
- local risk scoring from reusable model artifacts
- structured audit history for user actions and tool calls
- internal SQL migrations and seed data for platform-owned state

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

## Key Directories

- `frontend/`: Streamlit entrypoint, pages, and UI helpers
- `backend/`: API app, agent, auth, guardrails, retrieval, services, storage, and MCP gateway modules
- `integrations/`: upstream trade and risk adapters plus canonical external-data contracts
- `sql/`: schema migrations and seed data
- `data/`: local fixtures, knowledge inputs, and seeded assets
- `docs/`: requirements and supporting architecture notes

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

## Repository Contents

The repository includes:

- a backend health endpoint at `GET /health`
- a project-owned Streamlit shell with login or role-switch entry
- integration boundaries for trade and risk source adapters
- SQL migrations for core schemas, identity tables, conversation tables, and audit tables

## Notes

- `texts/` is intentionally ignored and treated as scratch or raw ideation space.
- Upstream projects are not required to expose remote APIs for local development.
- This repository is intended to be the only primary frontend entry for the overall solution.
