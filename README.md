# Chartered Vectorial

AI-powered investment analysis platform that ingests client portfolios, asks goal/risk questions, and returns risk metrics plus recommendations.

## How to Run

### Backend (FastAPI)

1. `cd backend`
2. Create venv: `python3 -m venv venv && source venv/bin/activate`
3. Install deps: `pip install -r requirements.txt`
4. Set env (example):
   - `DATABASE_URL=postgresql://user:password@localhost:5432/investmentadvisory`
   - `OPENROUTER_API_KEY=<key>`
   - `CORS_ORIGINS=http://localhost:5173`
5. Init tables (quick start):
   ```bash
   python3 - <<'PY'
   from app.database import Base, engine
   Base.metadata.create_all(bind=engine)
   print("tables ready")
   PY
   ```
6. Run API: `uvicorn app.main:app --reload --port 8000`

### Frontend (React + Vite)

1. `cd frontend`
2. Install deps: `npm install`
3. Set API base: `VITE_API_BASE_URL=http://localhost:8000`
4. Run dev server: `npm run dev` (opens http://localhost:5173)

## File Structure (core)

```
backend/
  app/
    main.py              # FastAPI app + CORS
    database.py          # SQLAlchemy engine/session
    models/              # client, risk, recommendation tables
    routes/              # HTTP endpoints (clients, analysis, portfolio)
    services/            # parsing, analysis, LLM wrapper, optimizers
    agents/              # multi-agent flows & prompts
frontend/
  src/
    api/analysisApi.ts   # HTTP client
    contexts/            # shared analysis state
    components/          # UI: chat, dashboard, forms, browser
    stages/              # multi-stage UX flow
```

## Key Architecture Decisions

- **Deterministic finance + AI narration**: All portfolio math (risk, allocation, optimizer) is pure Python; LLM only explains and suggests actions.
- **PostgreSQL via SQLAlchemy**: UUID-based records for clients and analyses; keeps history and repeatability.
- **Multi-stage workflow**: Onboarding (upload + basics) → Q&A for risk/goals → analysis → recommendations → dashboard.
- **Service layering**: Routes stay thin; services handle parsing, calculations, LLM calls; keeps testable units.
- **Frontend state via Context**: Single analysis context feeding the multi-tab dashboard and chat/intake flows.
- **OpenRouter integration**: Pluggable LLM provider with request logging/backoff.

## Challenges and Solutions

- **Rate/credit errors (402/429)**: Added OpenRouter retry/backoff and better error logging to surface provider responses.
- **DB drift (SQLite vs Postgres)**: Standardized on Postgres with `DATABASE_URL`; ensured table creation via SQLAlchemy metadata.
- **File parsing variance**: Built CSV-first parsing with deterministic fallbacks; kept PDF/Excel handling behind services.
- **Frontend stability**: Fixed JSX import/name mismatches and tightened type usage in shared context.

## If Given More Time

- **LangGraph orchestration**: Promote agents (intake, risk profiler, advisor copilot) into a stateful graph with streaming updates.
- **Real migrations**: Replace ad-hoc table creation with Alembic and CI migrations.
- **Document intelligence**: More robust PDF/statement extraction with table detection and validation loops.
- **Auth and roles**: Secure endpoints, add audit trails, and per-advisor access control.
- **Observability**: Structured logs, tracing, and metrics around LLM/tool latency and failures.
- **Production hardening**: Rate limiting, request size limits, async file uploads, and S3-backed storage for documents.
