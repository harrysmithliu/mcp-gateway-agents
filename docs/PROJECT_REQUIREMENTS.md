# MCP Gateway Agents Project Requirements

## 1. Purpose

This document defines the executable product and engineering requirements for the project rooted at `mcp-gateway-agents/`.

The project is a Python monolith for crypto trading intelligence and risk operations. It must provide a project-owned Streamlit workspace, a FastAPI backend, a LangChain-based agent orchestration layer, an MCP gateway, local trade and risk integrations, persistent operational data, and a path to retrieval, cache, and guardrails.

This document is the implementation baseline.

## 2. Product Summary

The system is an internal AI copilot for trading analysis and risk operations. It allows authorized users to:

- investigate unusual account, wallet, order, and trade activity
- ask natural-language questions about suspicious behavior
- run single-account and batch risk scoring
- retrieve policy, model, and case knowledge with evidence
- create alerts, recommendations, and review actions
- keep an auditable record of user actions, tool calls, and system decisions

The only user-facing entry must be the Streamlit application in this repository.

## 3. Core Architecture

The minimum target architecture is:

```text
Streamlit UI
  -> FastAPI Backend
  -> RBAC / Session Control
  -> LangChain Agent Engine
     -> Redis Cache / Chat Context
     -> RAG Retrieval Layer (Embedding + Vector Store)
     -> MCP Gateway
        -> TRADE tools
        -> RISK tools
        -> KNOWLEDGE tools
        -> OPS tools
     -> Claude-compatible LLM
     -> Guardrails
  -> PostgreSQL / Project Storage
  -> Streamlit response rendering
```

The first runnable closed loop must be:

`Streamlit -> FastAPI -> Agent -> MCP tools -> Postgres/Redis -> Streamlit`

The current implementation baseline must use LangChain for agent orchestration and Claude integration, while keeping the agent state, tool routing, and workflow boundaries compatible with a future migration or expansion to LangGraph.

Within the architecture, the retrieval stack must be explicitly treated as a RAG Retrieval Layer. This layer owns document chunking, embeddings, vector lookup, and evidence assembly for agent responses.

Embeddings and retrieval metadata must be persisted in the project-owned PostgreSQL data store rather than in a separate mandatory external vector database. The preferred implementation is PostgreSQL with `pgvector`, with `knowledge_documents`, `knowledge_chunks`, and `chunk_embeddings` serving as the canonical persistence model for RAG data.

## 4. Product Scope

### 4.1 In scope

- project-owned Streamlit UI
- FastAPI service endpoints
- RBAC-aware session and access control
- LangChain-based agent orchestration with tool calling
- MCP tool registry and tool execution layer
- project-owned PostgreSQL schemas, migrations, and seeds
- Redis-backed cache and short-term conversation context
- local adapters to trade and risk source assets
- RAG-based knowledge retrieval over internal documents
- alerting, case handling, and audit persistence
- local Docker Compose for developer runtime

### 4.2 Out of scope for the first major release

- real exchange order execution
- live upstream service dependencies as a requirement
- customer self-registration
- irreversible automated enforcement without approval
- multi-tenant SaaS hardening
- training pipeline redesign for the risk model

## 5. Business Users And RBAC

### 5.1 Supported roles

- `analyst`
- `risk_operator`
- `supervisor`
- `admin`

### 5.2 Permission intent

`analyst`

- can investigate accounts and wallets
- can query trade metrics and abnormal activity
- can run single-account and batch risk scoring
- can draft investigation summaries
- cannot execute sensitive operational actions

`risk_operator`

- inherits analyst capabilities
- can create and update alerts
- can submit manual review notes and action recommendations
- cannot approve the highest-impact actions alone

`supervisor`

- inherits risk operator capabilities
- can approve or reject sensitive actions such as freeze or release decisions
- can close high-severity cases

`admin`

- can manage users, roles, system switches, knowledge content, and audit access

### 5.3 Login and identity rules

- Login is the only platform entry.
- Users are provisioned by the backend or admin workflows. Self-registration is not supported.
- One browser tab represents exactly one active identity.
- Multi-tab usage is supported.
- A backend switch must control identity concurrency:
  - `0`: multi-tab is allowed, but only one identity may be active across the browser session
  - `1`: multi-tab with multiple identities is allowed

## 6. Upstream Inputs And Reuse Rules

The platform reuses fixed local assets in `integrations/` for the current version and must preserve a clean path to future upstream API integration.

### 6.1 Trade-side source assets

- `integrations/sources/trade_source/vendor/crypto_trade_plot/generate_mock_data.py`
- `integrations/sources/trade_source/vendor/crypto_trade_plot/crypto_transactions_30d.csv`
- `integrations/sources/trade_source/vendor/crypto_trade_plot/README.md`

### 6.2 Risk-side source assets

- `integrations/sources/risk_source/vendor/ml_risk_control/artifacts/xgboost/xgboost_credit_risk.joblib`
- `integrations/sources/risk_source/vendor/ml_risk_control/artifacts/xgboost/feature_schema.json`
- `integrations/sources/risk_source/vendor/ml_risk_control/artifacts/xgboost/run_summary.json`
- `integrations/sources/risk_source/vendor/ml_risk_control/artifacts/xgboost/threshold_selection_report.json`
- `integrations/sources/risk_source/vendor/ml_risk_control/artifacts/xgboost/cost_analysis_report.json`
- `integrations/sources/risk_source/vendor/ml_risk_control/artifacts/xgboost/calibration_report.json`
- `integrations/sources/risk_source/vendor/ml_risk_control/README.md`

### 6.3 Reuse rules

- Upstream assets are source material, not user-facing applications.
- This project must not depend on upstream frontends to complete workflows.
- The first implementation should prefer local adapters over network APIs.
- All upstream-specific paths, formats, and field names must stay inside `integrations/sources/`.

## 7. Repository Structure

The project structure must remain aligned with the following ownership model:

```text
mcp-gateway-agents/
├── docs/
├── frontend/
│   ├── app.py
│   ├── pages/
│   ├── components/
│   └── services/
├── backend/
│   ├── api/
│   ├── agent/
│   ├── auth/
│   ├── guardrails/
│   ├── retrieval/
│   ├── mcp_gateway/
│   ├── services/
│   └── storage/
├── integrations/
│   ├── sources/
│   │   ├── trade_source/
│   │   └── risk_source/
│   └── contracts/
├── data/
│   ├── seeds/
│   ├── fixtures/
│   └── knowledge/
├── sql/
│   ├── migrations/
│   └── seeds/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── smoke/
├── scripts/
├── compose.yaml
└── README.md
```

## 8. Module Responsibilities

### 8.1 `frontend/`

- owns the only user-facing interface
- contains login, dashboard, chat, scoring, alert, and audit views
- calls the backend through project-owned service wrappers

### 8.2 `backend/api/`

- exposes HTTP endpoints
- validates requests
- applies authentication and authorization
- persists session and audit context

### 8.3 `backend/agent/`

- owns LangChain-based orchestration logic
- integrates Claude-compatible chat models through LangChain abstractions
- chooses tool calls based on role and request type
- consumes RAG retrieval results, MCP tool outputs, cache context, and guardrail checks
- keeps message state, tool routing, and execution flow structured so later LangGraph adoption does not require API or frontend rewrites
- returns structured responses for UI rendering

### 8.4 `backend/mcp_gateway/`

- registers tools and resources
- provides stable internal invocation contracts
- exposes trade, risk, retrieval, and operations capabilities as MCP tools
- isolates tool discovery and tool registration from agent logic
- does not own core business logic, RAG implementation, or upstream-specific parsing

### 8.5 `backend/retrieval/`

- owns the RAG Retrieval Layer implementation
- handles document chunking, embedding generation, vector index access, and retrieval assembly
- prepares evidence payloads and citations for agent responses and knowledge-facing APIs
- uses the project-owned PostgreSQL vector store, preferably via `pgvector`, as the default persistence and query layer for embeddings

### 8.6 `backend/services/`

- owns project-native business services such as alerts, case actions, audit workflows, and knowledge administration
- coordinates storage, retrieval, and upstream-backed domain services behind backend-facing interfaces

### 8.7 `backend/storage/`

- owns relational persistence access patterns, repository helpers, and storage configuration
- supports both operational data access and vector-store integration boundaries where needed
- owns the PostgreSQL persistence boundary for retrieval records and vector-backed knowledge tables

### 8.8 `integrations/sources/`

- loads trade-side data and risk-side model artifacts
- normalizes upstream data to internal contracts
- owns all upstream path and format knowledge

### 8.9 `integrations/contracts/`

- defines canonical internal models
- prevents leakage of upstream-specific schemas into the rest of the codebase

## 9. Functional Requirements

### 9.1 Frontend

The frontend must support:

- login or role-switch entry
- chat workspace
- trade dashboard
- risk scoring workspace
- alert handling workspace
- evidence and report panel
- audit review page for privileged roles

### 9.2 Backend API

The backend must provide at least:

- health endpoint
- auth or demo session bootstrap endpoint
- chat request endpoint
- account lookup and account detail endpoints
- single-account and batch scoring endpoints
- alert and case endpoints
- audit query endpoint
- knowledge management and retrieval endpoints for privileged roles

### 9.3 Agent behavior

The agent must support:

- LangChain as the default orchestration framework for prompt flow, model binding, and tool invocation
- role-aware response shaping
- role-aware tool selection
- structured tool execution
- evidence-backed recommendations
- refusal or downgrade behavior for unauthorized requests
- a response structure that can grow from plain text into text plus evidence plus actions

The agent layer must not bypass LangChain by scattering direct model calls throughout API routes or tool modules.

Knowledge-facing MCP capabilities must be backed by backend-native retrieval or service modules rather than by upstream integration adapters alone.

### 9.4 MCP tool surface

Minimum tool inventory:

- `trade.query_metrics`
- `trade.query_account_activity`
- `trade.render_report`
- `risk.score_account`
- `risk.batch_score`
- `knowledge.search`
- `ops.create_alert_or_action`
- `audit.fetch_recent_events`

### 9.5 Guardrails

Guardrails must cover:

- blocking of unapproved sensitive actions
- required evidence for high-impact recommendations
- unsupported-claim checks
- prompt injection resistance for retrieved knowledge
- role-based action restrictions

## 10. Data Model Requirements

The platform must support the following table families.

### 10.1 Identity and access

- `users`
- `roles`
- `user_role_bindings`
- `api_tokens`

### 10.2 Conversation and audit

- `chat_sessions`
- `chat_messages`
- `tool_call_logs`
- `audit_events`

### 10.3 Trading domain

- `accounts`
- `wallets`
- `orders`
- `trades`
- `positions`
- `price_ticks`

### 10.4 Risk and operations

- `risk_scores`
- `risk_features_snapshot`
- `risk_alerts`
- `case_actions`

### 10.5 Knowledge and retrieval

- `knowledge_documents`: source documents and document-level metadata
- `knowledge_chunks`: chunked retrieval units derived from source documents
- `chunk_embeddings`: embeddings persisted in the project-owned PostgreSQL vector store, preferably through `pgvector`

## 11. Seed And Mock Data Requirements

The repository must contain enough local data to demonstrate realistic end-to-end workflows.

### 11.1 Trading data

- orders
- fills or trades
- positions
- wallet-level or account-level summaries
- price series
- anomaly windows

### 11.2 Risk data

- account age
- large-amount frequency
- failed transaction rate
- unusual-hour activity
- KYC tier
- risk feature snapshots
- single and batch score results

### 11.3 Knowledge data

- risk rules
- model card content
- threshold guidance
- abnormal trading case examples
- investigation SOP documents

### 11.4 Demo identities

- at least one seeded user for each supported role

## 12. Closed-Loop Extensibility Requirements

The earliest runnable closed loop is under schedule pressure and must be delivered quickly, but its code must not trap the project in a dead-end design.

The first closed-loop implementation must therefore preserve the following extension seams from day one:

- request and response DTOs for chat, scoring, and alert actions must be versionable
- MCP tools must be registered through a registry abstraction, not hard-coded inside the agent
- LangChain-specific model, prompt, and tool wiring must stay inside `backend/agent/` so the rest of the system depends on internal service contracts rather than framework details
- RAG implementation must live in `backend/retrieval/` or an equivalent backend-native module rather than being modeled as an upstream integration concern
- retrieval records, chunk metadata, and embeddings must remain persistable inside the project-owned PostgreSQL vector store so later replay, re-indexing, and local operation do not depend on a mandatory external vector database
- the agent must call tool adapters through interfaces or service boundaries that can later add retrieval, cache, and guardrails without breaking callers
- the orchestration state model must be compatible with later LangGraph-style node or graph execution if the workflow becomes more complex
- source adapters must emit canonical internal contracts, never raw upstream payloads
- the frontend service layer must call typed backend endpoints, not import backend modules directly
- all sensitive actions must already flow through an approval-aware operation model, even if the first release uses simple approval stubs
- persistence must keep chat, audit, and tool logs separate so later replay and analytics can be added
- retrieval, cache, and guardrail hooks must exist in the orchestration flow even if their first implementation is minimal

## 13. Non-Functional Requirements

### 13.1 Language

All repository artifacts must be written in English, including documentation, comments, labels, and developer-facing notes.

### 13.2 Maintainability

- clear module boundaries
- environment-driven configuration
- replaceable adapters
- isolated vendor-specific logic

### 13.3 Testability

- unit tests for adapters, contracts, RBAC checks, backend service logic, retrieval logic, and MCP tool logic
- integration tests for API and tool paths
- smoke tests for startup and the main workflow

### 13.4 Security

- no hard-coded secrets
- role-based access control on all sensitive operations
- audit logging for tool calls and operator actions

### 13.5 Observability

- structured logs
- request correlation where practical
- explicit tool execution logging
- retrieval pipeline and ingestion logging for chunking, embedding, vector persistence, and search behavior
- actionable error messages for UI and developer debugging

## 14. Delivery Strategy

Development must be organized into independently pushable batches. Every batch must:

- keep the repository in a runnable or at least test-passing state
- include updated docs for the new surface area
- include tests or executable verification steps for the delivered scope
- be safe to push to git as a standalone checkpoint

Phase grouping:

- Phase 1: Batch 1 to Batch 4
- Phase 2: Batch 5 to Batch 7

The first runnable closed loop must be completed by Batch 2.

## 15. Batch Plan

### Batch 1. Foundations And Stable Contracts

Goal:

- establish the project shape needed for fast follow-on delivery

Scope:

- repository structure
- configuration model
- FastAPI entrypoint
- Streamlit entrypoint
- base RBAC model
- LangChain dependency and agent module boundary
- retrieval module boundary and service module boundary
- canonical contracts
- initial SQL schemas for IAM, conversation, audit, trading, risk, and knowledge
- local runtime and seed scaffolding

Deliverables:

- working backend bootstrap with health endpoint
- working frontend bootstrap with login or role-switch entry
- settings and environment template
- agent module scaffold prepared for LangChain-based orchestration
- retrieval module scaffold for chunking, embeddings, and vector access
- backend service module scaffold for project-native operations workflows
- first migration set for required schemas and core tables
- initial internal contracts under `integrations/contracts/`
- source adapter skeletons and MCP registry skeleton
- document describing the product and requirements

Completion metrics:

- backend starts locally and `GET /health` returns success
- frontend starts locally and renders the entry page
- migrations apply successfully on a fresh database
- at least one test validates boot or contract behavior
- the repository declares the LangChain-based agent direction clearly enough that later implementation will not default to ad hoc orchestration
- the repository structure makes it clear that RAG and operations logic are backend-native capabilities rather than upstream integration modules
- no module outside `integrations/sources/` depends on vendor paths or vendor field names

Git push boundary:

- one commit or a small coherent commit set that leaves local startup intact

### Batch 2. Earliest Runnable Closed Loop

Goal:

- deliver the smallest end-to-end workflow that proves the target architecture

Scope:

- Streamlit chat submission
- FastAPI chat endpoint
- LangChain-based agent orchestration service
- backend-native retrieval and operations service wiring
- MCP tool registry and first tool implementations
- PostgreSQL reads and writes for sessions, messages, and audit events
- Redis usage for short-term request context or minimal cache
- trade metrics query path
- single-account risk scoring path
- alert creation path

Deliverables:

- a user can enter through Streamlit, submit a request, receive an answer, and create at least one persisted operational record
- first LangChain runnable path that binds Claude, prompt state, and MCP-exposed tools through the project agent service
- first MCP-exposed business path backed by upstream adapters for trade and risk plus backend-native services for operations
- first implementations of:
  - `trade.query_metrics`
  - `risk.score_account`
  - `ops.create_alert_or_action`
- persisted chat sessions, chat messages, tool logs, and audit events
- seeded trading and risk demo data sufficient for the closed loop
- smoke test or scripted verification for the end-to-end flow

Completion metrics:

- the flow `Streamlit -> FastAPI -> Agent -> MCP tools -> Postgres/Redis -> Streamlit` runs locally
- the runnable agent path uses LangChain for model and tool orchestration instead of direct ad hoc model calls
- one analyst prompt returns trade or risk output grounded in project data
- one alert or action record is written to the database
- audit records capture the user request and tool usage
- batch output remains extensible through the interfaces defined in Section 12

Git push boundary:

- a standalone push that another developer can pull, start, seed, and demo without extra hidden setup

### Batch 3. Expanded Phase-1 Domain Surface

Goal:

- complete the remaining essential product surface around the first closed loop

Scope:

- account search and account detail APIs
- batch scoring
- richer trade activity queries
- alert status updates and case action flows
- fuller domain seeds for accounts, wallets, orders, trades, positions, price ticks, and risk features
- role-aware API restrictions beyond basic gating

Deliverables:

- account investigation views and APIs
- `risk.batch_score`
- richer `trade.query_account_activity`
- `audit.fetch_recent_events`
- seeded role-based demo users
- integration tests for role-sensitive endpoints

Completion metrics:

- analyst, risk operator, supervisor, and admin flows diverge correctly by permission
- batch scoring persists multiple results
- account and alert views are backed by real project data
- core Phase-1 domain tables are populated and queryable

Git push boundary:

- the repository remains runnable and demoable with expanded workflows

### Batch 4. Phase-1 Completion And Operational Hardening

Goal:

- complete the remainder of the first release surface without changing the earlier architecture

Scope:

- multi-page frontend workspace
- report and evidence panel
- approval-ready supervisor actions
- better audit review surfaces
- stronger error handling and structured logging
- compose-based local startup

Deliverables:

- dashboard, chat, scoring, alerts, and audit pages
- approval-aware sensitive action flow
- local compose stack for required services
- operator-oriented runbook for local setup

Completion metrics:

- an analyst can investigate and draft findings
- a risk operator can create and update alerts
- a supervisor can approve or reject a sensitive action
- local compose startup runs the required services successfully

Git push boundary:

- a self-contained Phase-1 product milestone suitable for internal demo

### Batch 5. Retrieval And Evidence Layer

Goal:

- add evidence-backed answers and knowledge administration

Scope:

- document ingestion
- chunking
- embeddings
- vector retrieval
- PostgreSQL and `pgvector` enablement for project-owned vector persistence
- knowledge search tool
- evidence rendering in UI
- LangChain retrieval hooks or chains integrated into the agent flow
- MCP exposure of retrieval-backed knowledge capabilities through `backend/mcp_gateway/`

Deliverables:

- `knowledge.search`
- backend-native retrieval service for chunking, embeddings, vector lookup, and evidence assembly
- migrations and storage setup for project-owned PostgreSQL vector persistence, preferably via `pgvector`
- seeded knowledge documents and chunk records
- embeddings written to `chunk_embeddings`
- retrieval-backed answers with citations
- admin workflow for knowledge refresh or indexing

Completion metrics:

- a knowledge-backed prompt returns cited evidence
- embeddings are persisted in `chunk_embeddings` inside the project-owned PostgreSQL vector store and are queryable by the retrieval flow
- retrieved content is visible in the UI
- ingestion can be rerun safely on local data
- the retrieval flow does not require a mandatory external vector database

Git push boundary:

- the product still runs even if retrieval is disabled by configuration

### Batch 6. Cache, Chat History, And Guardrails

Goal:

- improve efficiency, continuity, and safety

Scope:

- Redis-backed response cache
- chat history retrieval
- sensitive-action guardrails
- evidence requirement checks
- unsupported-claim checks
- LangChain memory or message-history integration at the service boundary

Deliverables:

- cache-aware orchestration
- session history replay support
- guardrail policy enforcement
- tests for restricted actions and unsupported outputs

Completion metrics:

- repeated eligible prompts can hit cache
- chat context is restored within a session
- high-impact actions are blocked or downgraded without required role and evidence

Git push boundary:

- behavior changes are covered by tests and remain explainable to operators

### Batch 7. Phase-2 Finish, QA, And Delivery Readiness

Goal:

- make the system easier to operate, verify, and hand over

Scope:

- full smoke coverage
- test data reset workflows
- admin-facing operational settings
- documentation cleanup
- packaging and developer ergonomics

Deliverables:

- repeatable seed and reset commands
- smoke tests for the main flows
- operational documentation
- final local delivery package

Completion metrics:

- a fresh developer can set up, seed, run, and verify the system from repository docs
- main flows have automated or scripted verification
- the product can be handed off without tribal knowledge

Git push boundary:

- the repository is ready for regular collaborative iteration

## 16. Definition Of Done

The project is considered to meet this requirements document when all of the following are true:

- the Streamlit application is the only user-facing entry
- the backend, agent, MCP tools, storage, and audit trail work together
- the agent layer is implemented through LangChain-based orchestration rather than ad hoc direct model wiring
- local trade and risk integrations are usable through stable internal contracts
- at least one realistic analyst-to-operator-to-supervisor workflow is demonstrated
- evidence-backed knowledge retrieval exists
- RAG embeddings and retrieval records are persisted in the project-owned PostgreSQL vector store, preferably through `pgvector`
- cache, chat history, and guardrails are integrated
- every delivery batch has explicit deliverables and measurable completion criteria
