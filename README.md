# Multi-Agent Code Analysis & Documentation System
**Purpose:** Intelligent codebase documentation and analysis using multi-agent orchestration.

## Features
- Large repository analysis with intelligent preprocessing and important-file identification.
- Multi-agent orchestration (LangGraph hooks) — each agent has a dedicated responsibility.
- Realtime progress visibility via Streamlit + server-sent events / Redis pubsub.
- Pause / Resume control for interactive analysis flows.
- Visual flow generation using Mermaid diagrams.
- Role-based access (user / admin) with JWT auth.
- Observability & traceability — hooks for langfuse and structured tracing.
- Storage: Postgres with pgvector for embeddings; Redis for task coordination.

## Tech stack
- LangGraph (orchestration hooks)
- FastAPI (backend API & agent orchestration)
- Streamlit (dashboard & control plane)
- PostgreSQL + pgvector (vector store)
- Redis (pub/sub, pause/resume control)
- MCP Server (placeholder for message coordination)
- langfuse (observability placeholder), llm (your chosen LLM integration)
- Mermaid for visual flows

## Quick start (development)
1. Install Docker & Docker Compose.
2. Copy `.env.example` to `.env` and fill secrets (JWT_SECRET, DB credentials, OPENAI_KEY, LANGFUSE_KEY).
3. Run `docker compose up --build`
4. FastAPI docs: http://localhost:8000/docs
5. Streamlit dashboard: http://localhost:8501

## What's included
- `backend/` — FastAPI app and orchestration logic.
- `agents/` — agent skeletons (ingest, metadata, summarizer, docgen, observability).
- `dashboard/` — Streamlit control UI (pause/resume, progress, mermaid rendering).
- `infra/` — docker-compose, postgres migrations, and sample SQL.
- `docs/` — architecture, API spec, sequence diagrams.
- `scripts/` — helper scripts (create env, run locally).
