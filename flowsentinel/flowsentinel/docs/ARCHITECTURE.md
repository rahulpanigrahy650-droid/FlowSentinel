# FlowSentinel - Architecture and Project Analysis

## 1. Problem and goals

IT support teams lose time on three things: working out how bad an incident is, working out who should
own it, and finding the runbook that fixes it. FlowSentinel automates those three steps and keeps a human
in control of the outcome.

| Goal | How it is met |
|---|---|
| Faster triage | Category, severity, summary, SLA due time and owning team are set within seconds of reporting |
| Faster resolution | RAG over technical documentation produces a cited, step-by-step plan |
| Safe automation | Critical incidents are escalated, not auto-handled; the LLM cannot downgrade hard-critical signals; low-confidence answers carry a warning |
| Continuous improvement | Agent feedback is recorded; resolved incidents can be added to the knowledge base |
| Works anywhere | Full offline mode (rules + extractive answers + local embedder); LLM and real embeddings are opt-in |

## 2. Components

```
frontend/ (React + Vite)         Overview · Incidents · Incident detail · Knowledge base
backend/app/
  api/            REST routers: incidents, knowledge, analytics
  services/       incident_service (create/analyse/update/learn), ingestion (seed KB), runtime (singletons)
  workflow/       LangGraph graph + framework-free node functions + state schema
  core/           heuristics (rules), llm (LangChain adapter), embeddings, chunking, vectorstore
  models.py       SQLAlchemy: Incident, IncidentEvent, Document, Chunk(embedding)
backend/knowledge_base/   12 sample runbooks (Markdown), indexed at startup
```

## 3. The LangGraph workflow

```
START -> triage -> retrieve -> grade --weak & first try--> retrieve (rewritten query)
                                  \--ok or already retried--> draft_resolution -> decide_route -> END
```

| Node | What it does |
|---|---|
| triage | LLM structured output (category, severity, summary, confidence, rationale) or rule-based fallback; applies the severity floor |
| retrieve | Embeds `title + summary`, cosine search for the top-k passages |
| grade | Corrective-RAG check: if the best similarity is below `MIN_SCORE`, rewrite the query (LLM, or the raw description) and retrieve once more |
| draft_resolution | LLM answer constrained to the retrieved passages with `[n]` citations; or an extractive answer built from the runbook steps, with a low-confidence warning when the match is weak |
| decide_route | `critical` -> **escalate** (status escalated, on-call team); confident match -> **suggested**; otherwise -> **manual** triage |

Every node appends to an audit trace that is stored with the incident and shown in the UI.
Node functions contain no framework code, so they are unit-tested with fake retrievers and LLMs.

## 4. Triage logic

* Category: ten categories (network, security, database, identity & access, email & collaboration, hardware,
  infrastructure, application, service request, other), each mapped to an owning team.
* Severity (critical / high / medium / low): additive score from impact signals (outage, all users, production,
  breach), user counts ("40 users"), and low-urgency phrases ("how do I", "not urgent"). Hard-critical phrases
  force `critical`. SLA targets: 1 h / 4 h / 24 h / 72 h.
* Agents can override severity and category; overrides are logged and survive re-analysis.

## 5. Knowledge retrieval (RAG)

1. Markdown is split by heading (keeping the heading path) and then by paragraph up to `CHUNK_CHARS` with overlap.
2. Each chunk is embedded as `title + heading + text`.
3. PostgreSQL stores vectors in a pgvector `vector(EMBEDDING_DIM)` column with an HNSW cosine index; SQLite
   (dev/tests) stores JSON and searches exactly with numpy.
4. Embeddings: OpenAI via LangChain when a key is set (dimension-truncated to match the column), otherwise a
   deterministic hashing embedder (stemmed unigrams and bigrams). After switching, call `POST /api/knowledge/reindex`.

Measured on the bundled runbooks with the offline embedder: 12 of 12 representative incidents retrieve the
correct runbook first. Absolute similarity scores are low for this lexical embedder, which is why the
thresholds default to 0.10 / 0.20 and are configurable.

## 6. Data model

* `incidents`: title, description, reporter, status, analysis_status, category, severity (+ overridden flag),
  summary, confidence, suggested_resolution, route, assigned_team, analysis (JSON: trace, passages, rationale),
  resolution_notes, feedback, timestamps, SLA due time.
* `incident_events`: audit log (created, analysed, status, override, feedback, note).
* `documents` / `chunks`: knowledge base and its vector index.

## 7. Design decisions

| Decision | Reason |
|---|---|
| Asynchronous analysis (background task + polling) | LLM calls take seconds; reporting an incident must stay instant |
| Offline mode is first-class | Demos, CI and air-gapped sites work without keys; every LLM call has a fallback |
| LLM floor, not ceiling, on severity | An under-triaged outage costs more than an over-triaged one |
| Citations and low-confidence warnings | Agents can verify the source instead of trusting generated text |
| Closing the loop (feedback, learn from resolved incidents) | Retrieval quality improves with use |
| One dialect-aware vector store | Same code path for pgvector in production and SQLite in tests |

## 8. Risks and recommended next steps

1. Authentication, roles and per-team visibility (OIDC); audit who changed what.
2. Job queue (Celery/RQ) and retries for analysis; rate limiting; request logging and tracing (LangSmith/OpenTelemetry).
3. Alembic migrations; backup policy for the vector table.
4. Evaluation set: replay historical incidents and track top-1 retrieval accuracy and severity agreement.
5. Similar-incident detection and duplicate grouping (embed incidents, not only documents).
6. Connectors: ServiceNow/Jira/Slack/Teams for intake and notifications; PagerDuty for escalations.
7. Prompt-injection hardening: incident text is untrusted input to the LLM; the current design limits blast radius
   (no tool use, output is text shown to an agent) but add output filtering before any auto-remediation.
