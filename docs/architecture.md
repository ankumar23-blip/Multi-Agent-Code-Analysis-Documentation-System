# Architecture Overview

- Ingest Agent: clones repository, tokenizes files, chunking for embedding.
- Metadata Agent: extracts file importance using heuristics (size, dependency graph, change frequency).
- Summarizer Agent: produces embeddings and short summaries using LLM.
- Doc Generator Agent: assembles documentation pages and designs mermaid flows.
- Observability Agent: emits structured traces to langfuse and stores agent traces for traceability.

Orchestration:
- LangGraph can be used to implement complex agent flows; our orchestrator provides a simple pipeline example.
- Redis provides pause/resume coordination and pub/sub for realtime updates.
- Postgres + pgvector stores embeddings for semantic search and context boosting.

Security:
- Role-based JWT auth with Admin and User roles (see `backend/auth.py`).
