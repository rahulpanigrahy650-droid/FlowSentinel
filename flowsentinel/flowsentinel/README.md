# FlowSentinel

IT incident management and intelligent resolution. When an incident is reported, FlowSentinel
analyses it, assigns a category and severity, searches your technical documentation (RAG) for the
relevant fix, drafts a cited troubleshooting plan, and routes the ticket (auto-suggest, human triage
or on-call escalation).

**Stack:** Python · FastAPI · React (Vite) · PostgreSQL + pgvector · LangGraph · LangChain · REST

```
React UI ──REST──> FastAPI ──> LangGraph workflow ──> LangChain LLM (Claude / OpenAI, optional)
                      │              └─ retrieve ───> pgvector (PostgreSQL)
                      └──────────────> PostgreSQL (incidents, events, documents, chunks)
```

## Quick start (Docker)

```bash
cp .env.example .env        # optional: add an API key for LLM-quality triage and answers
docker compose up --build
```

* UI: http://localhost:8080  ·  API docs: http://localhost:8000/docs
* 12 sample runbooks are indexed on first start. Load demo incidents:
  `docker compose exec backend python -m scripts.seed_demo`

No API key is required. Without one the platform runs **offline**: rule-based triage, extractive
answers built from the retrieved runbooks, and a built-in hashing embedder. Adding
`ANTHROPIC_API_KEY` or `OPENAI_API_KEY` switches triage and resolution drafting to the LLM
(LangChain structured output); an OpenAI key also switches embeddings.

## Local development

```bash
# backend (SQLite, no Postgres needed)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload            # http://localhost:8000

# frontend
cd frontend
npm install
npm run dev                               # http://localhost:5173 (proxies /api to :8000)
```

Tests: `cd backend && pytest` (pure-logic tests plus an end-to-end API test on SQLite).

## How an incident flows

1. `POST /api/incidents` stores the incident and returns immediately.
2. A background task runs the LangGraph workflow:
   `triage → retrieve → grade ⟲ (rewrite query once if weak) → draft_resolution → decide_route`
3. The result (category, severity, summary, cited resolution, sources, workflow trace, SLA due time,
   assigned team) is saved; the UI polls until `analysis_status` is `done`.
4. Agents can override severity/category, mark the suggestion helpful or not, and resolve the incident.
   Resolving with "add to knowledge base" turns the notes into a new indexed document, so the system
   learns from every fix.

Safety rule: the LLM may raise severity, but hard-critical signals (ransomware, data loss, production
down, data breach…) can never be downgraded by it.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | SQLite file (Postgres in compose) | `postgresql+psycopg://user:pass@host/db` |
| `LLM_PROVIDER` | `auto` | `auto`, `anthropic`, `openai`, `none` |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | – / `claude-sonnet-5-5` | |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | – / `gpt-4o-mini` | |
| `EMBEDDING_PROVIDER` | `auto` | `auto`, `openai`, `hashing` |
| `EMBEDDING_DIM` | `1024` | vector column size; call `POST /api/knowledge/reindex` after changing |
| `MIN_SCORE` / `AUTO_SCORE` | `0.10` / `0.20` | relevance and "confident suggestion" thresholds (tune per embedding model) |
| `AUTO_SEED` | `true` | index `backend/knowledge_base/*.md` at startup |

## API summary

| Method | Path | |
|---|---|---|
| POST/GET | `/api/incidents` | create; list with `status`, `severity`, `category`, `q`, `limit`, `offset` |
| GET/PATCH | `/api/incidents/{id}` | detail with activity log; update status/severity/category/team/resolution |
| POST | `/api/incidents/{id}/reanalyze` · `/feedback` | re-run workflow; helpful / not helpful |
| GET/POST | `/api/knowledge/documents` | list; add Markdown/text |
| POST | `/api/knowledge/documents/upload` · `/search` · `/reindex` | upload file; semantic search; re-embed all |
| DELETE | `/api/knowledge/documents/{id}` | |
| GET | `/api/analytics/summary` | counts by severity/category, MTTR, SLA breaches, suggestion/helpful rates |
| GET | `/api/health` | database, LLM and embedding status |

## What has and has not been verified

The code was assembled in a sandbox without network access, so the full stack was **not** started there.

* Verified: all pure-logic tests pass (embedder, chunking, rule-based triage, every workflow node including
  retry, LLM-failure fallback and the severity floor, run against the 12 bundled runbooks); every Python
  file compiles; every React file parses and the app bundles with esbuild.
* Not run here: FastAPI/SQLAlchemy/pgvector/LangGraph/LangChain imports, the Docker images, the browser UI,
  and live LLM calls. Expect to fix small integration issues on first run (`pytest` will tell you quickly:
  `tests/test_api.py` exercises the whole API on SQLite).

## Known limits / next steps

No authentication or roles (add OAuth/OIDC before exposing it); analysis runs in FastAPI background tasks
(move to a queue such as Celery/RQ for scale); schema is created with `create_all` (add Alembic migrations);
the offline embedder is lexical, so use real embeddings for production-quality retrieval; incidents are not yet
de-duplicated or linked to similar past incidents; no ITSM connectors (ServiceNow/Jira) or notifications.
