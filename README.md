# Scentfolio

Scentfolio is a local-first fragrance tracker. Keep an owned collection and a
saved list, export either as CSV, and explore notes and similarities. AI-assisted
lookup fills in a draft you can review and edit before saving.

## Run locally

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and Node.js
24 with npm. If you use nvm, run `nvm install` from the repo root. uv uses the
Python 3.13 version specified in `backend/.python-version`.

In one terminal, from the repo root:

```sh
(cd backend && uv sync --locked)
./backend/run.sh
```

In a second terminal, from the repo root:

```sh
cd frontend
npm ci
npm run dev
```

Open [Scentfolio](http://localhost:5173). Vite sends `/api` requests to
[FastAPI on port 8000](http://localhost:8000/docs).

### Local data and AI features

The backend stores your data in `backend/scentfolio.db`. Set
`SCENTFOLIO_DB_URL` in the shell before starting the backend to use a different
database, such as a scratch SQLite file.

For AI lookup, note enrichment, and family reclassification, create
`backend/.env` from `backend/.env.example`, set `ANTHROPIC_API_KEY`, and restart
the backend. The app can browse and export your data without a key.

## Check changes

From `backend/`:

```sh
uv run --locked ruff format --check .
uv run --locked ruff check .
SCENTFOLIO_DB_URL=sqlite:///:memory: uv run --locked pytest
```

From `frontend/`:

```sh
npm run format:check
npm run lint
npm test
npm run build
```

Run `uv run --locked ruff format .` in `backend/` and `npm run format` in
`frontend/` to apply formatting. The test suites exercise AI-backed flows with
mocks and run without an API key.

See the [repo guide](docs/README.md) for where to make changes.
