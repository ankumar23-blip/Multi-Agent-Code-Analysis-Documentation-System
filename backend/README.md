# Backend (FastAPI) Service

## Quick Start

### 1. Create and activate a virtual environment (recommended)

```bash
# From the project root (one level above backend/)
python -m venv .venv

# Activate (PowerShell on Windows)
.\.venv\Scripts\Activate.ps1

# Activate (bash/zsh on macOS/Linux)
source .venv/bin/activate
```

**PowerShell execution policy note:** If you see a security error, run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
```
Then activate again.

### 2. Install dependencies

```bash
pip install -r backend/requirements.txt
```

### 3. Set environment variables (optional for local dev)

```powershell
# Set Claude API key if using Claude Haiku 4.5
$env:CLAUDE_API_KEY = 'your-anthropic-key'

# Or set OpenAI key if preferring GPT models
$env:OPENAI_API_KEY = 'your-openai-key'

# Override default model (defaults to claude-haiku-4.5)
$env:DEFAULT_LLM_MODEL = 'claude-haiku-4.5'

# Optional: set Redis and database URLs (for production/Docker)
$env:REDIS_URL = 'redis://localhost:6379/0'
$env:DATABASE_URL = 'postgresql+asyncpg://user:pass@localhost:5432/code_analysis'
```

### 4. Start the server

```bash
# From project root, with venv activated:
python -m uvicorn asgi:app --reload
```

Server runs at **http://127.0.0.1:8000**

## API Endpoints

- **POST** `/api/start-analysis` — Start a code analysis job
  - Body: `{ "repository_url": "...", "options": {...} }`
  - Returns: `{ "job_id": "uuid" }`

- **GET** `/api/jobs/{job_id}/status` — Get job status
  - Returns: `{ "status": "queued|running|completed|paused", "progress": 0.0-1.0, "mermaid": "..." }`

- **POST** `/api/control/{job_id}/pause` — Pause a running job
- **POST** `/api/control/{job_id}/resume` — Resume a paused job

- **GET** `/api/docs/{job_id}/mermaid` — Fetch final Mermaid diagram

## Interactive API Documentation

- **Swagger UI:** http://127.0.0.1:8000/docs (try endpoints here)
- **ReDoc:** http://127.0.0.1:8000/redoc (alternative format)

## Architecture

- **Orchestrator** (`backend/workers/orchestrator.py`): Coordinates multi-agent pipeline
- **Agents** (`backend/agents/`): Modular implementations
  - `ingest.py` — Fetch and parse repository
  - `metadata.py` — Extract code structure
  - `summarizer.py` — Generate summaries
  - `docgen.py` — Create documentation
  - `manager.py` — Agent lifecycle & control
  
- **LLM Provider** (`backend/utils/llm_provider.py`): Router for Claude (Anthropic) and OpenAI
  - Reads `DEFAULT_LLM_MODEL` env var (defaults to `claude-haiku-4.5`)
  - Uses `CLAUDE_API_KEY` for Claude models
  - Falls back to `OPENAI_API_KEY` for other models

- **Persistence**:
  - PostgreSQL + pgvector for code embeddings (optional, gracefully skipped if unavailable)
  - Redis for job state & distributed control (optional, in-memory fallback in dev)

## Database Setup (optional for Docker/production)

Run SQL migrations from `infra/init_db.sql` against your Postgres instance.
**Note:** In local dev mode, the app starts without a live database.

## Enable Claude Haiku 4.5 for All Clients

Set the environment variable before starting the server:

```powershell
$env:DEFAULT_LLM_MODEL = 'claude-haiku-4.5'
$env:CLAUDE_API_KEY = 'sk-ant-...'
python -m uvicorn asgi:app --reload
```

Or in `.env` (if using python-dotenv):
```
DEFAULT_LLM_MODEL=claude-haiku-4.5
CLAUDE_API_KEY=sk-ant-...
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'backend'` | Ensure you're running from the project root, not from inside `backend/` folder |
| `uvicorn: command not found` | Use `python -m uvicorn asgi:app --reload` instead of `uvicorn ...` |
| `[WARNING] Database initialization skipped` | Expected in local dev. Set `DATABASE_URL` env var to use a live database |
| `CLAUDE_API_KEY not set` | If using Claude, export `CLAUDE_API_KEY` before starting the server |
| Execution policy error on PowerShell | Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force` |

