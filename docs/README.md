# Repo guide

Start with the [root README](../README.md) to install, run, and check Scentfolio.
See [Architecture](architecture.md) for runtime boundaries and capacity.

| If you’re changing | Start here |
| --- | --- |
| Navigation or routes | [React routes](../frontend/src/App.tsx) |
| Theme, layout, or page styles | [Stylesheet entry point](../frontend/src/styles.css), [style files](../frontend/src/styles/) |
| Collection, saved list, or CSV export | [Collection view](../frontend/src/views/Collection.tsx), [perfume endpoints](../backend/app/api.py), [perfume storage](../backend/app/repository.py) |
| Lookup or batch add | [Add view](../frontend/src/views/Add.tsx), [BatchAdd](../frontend/src/views/BatchAdd.tsx), [AI work](../backend/app/ai_work.py), [provider transport](../backend/app/llm.py) |
| Note glossary or enrichment | [Glossary](../frontend/src/views/Glossary.tsx), [note detail](../frontend/src/views/NoteDetail.tsx), [note endpoints](../backend/app/api.py) |
| Insights or similarity | [Insights view](../frontend/src/views/Insights.tsx), [insight queries](../backend/app/queries.py) |
| SQLite schema or startup | [ORM models](../backend/app/models.py), [schema upgrades](../backend/app/db.py), [session setup](../backend/app/deps.py) |

React views call the [API client](../frontend/src/api.ts). Vite forwards
`/api` to FastAPI, whose routes call the [repository](../backend/app/repository.py)
for storage and [queries](../backend/app/queries.py) for insights. Shared React
components live in [`frontend/src/components/`](../frontend/src/components/).
Frontend tests sit beside the files they cover, and Python tests live in
[`backend/tests/`](../backend/tests/).

## Design history

The [dated feature specs](superpowers/specs/) and
[original implementation plan](superpowers/plans/2026-07-09-perfume-tracker.md)
record the decisions made as Scentfolio evolved. Use the current code and
tests to check behavior.
