# Notes & Next Steps to finish the system

Key engineering tasks:
1. Implement repo cloning in ingest agent (gitpython or subprocess).
2. Implement syntax-aware chunking (tree-sitter or simple line-based heuristics).
3. Wire up LLM provider (OpenAI, Anthropic, or local LLM) for embeddings & summarization.
4. Replace in-memory job controls with Redis-based distributed locks / pubsub.
5. Implement LangGraph flow definitions and adapters to call agents reliably.
6. Add PostgreSQL models and persistent job tracing tables.
7. Add tests: unit tests for agents and integration tests for orchestration.
8. Harden auth: user management, refresh tokens, and secure storage of secrets.
9. Add CI (GitHub Actions) and container build pipeline.
10. Add sample README for interview demo and talking points for SDE/PM.

If you want, I can implement items 1-4 next (repo cloning, chunking prototype, LLM wiring, Redis controls).
