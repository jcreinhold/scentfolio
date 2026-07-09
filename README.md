# Scentfolio — Perfume Tracker

Local-first app to catalogue perfumes with AI-assisted note lookup. Type a perfume
name and a Claude web-search agent pulls in the top/heart/base notes, perfumer, house,
year, scent family, and a description. Browse your collection, search by note, explore
insights, and learn scents through a cross-linked note glossary.

## Prerequisites
- Python 3.13 with [`uv`](https://github.com/astral-sh/uv) installed
- Node.js 18+ and npm
- An Anthropic API key (for perfume lookups)

## Run
1. **Backend:** copy `backend/.env.example` to `backend/.env` and add your `ANTHROPIC_API_KEY`, then:
   ```bash
   ./backend/run.sh
   ```
   Serves on http://localhost:8000. (The venv already exists at `backend/.venv`; if you need to recreate it: `cd backend && uv venv --python 3.13 .venv && source .venv/bin/activate && uv pip install -r requirements.txt`.)
2. **Frontend:**
   ```bash
   cd frontend && npm run dev
   ```
   Serves on http://localhost:5173 and proxies `/api` to the backend.
3. Open http://localhost:5173.

## Test
- **Backend:** `cd backend && source .venv/bin/activate && pytest`
- **Frontend:** `cd frontend && npx vitest run`

## Architecture
- `backend/` — FastAPI + SQLAlchemy + SQLite. Notes are normalized into their own
  table so "which perfumes have this note" and the glossary are direct joins. The
  lookup agent (`app/agent.py`) calls Claude with the built-in web search tool and
  returns a validated draft that you confirm before saving.
- `frontend/` — React + Vite + TypeScript. Three areas: Collection (search by name or
  note, filter by family/format), Insights (note frequency, family grouping,
  similarity — charts via Recharts), and the Note Glossary.

## Notes
- Data lives in `backend/scentfolio.db` (SQLite). The schema is Postgres-portable for
  a future hosted deployment.
- Nothing is saved without your confirmation; the lookup draft is fully editable.
