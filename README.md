# Scentfolio

Scentfolio is a local-first fragrance tracker. Keep an owned collection and a
saved list, export either as CSV, and explore notes and similarities. AI-assisted
lookup fills in a draft you can review and edit before saving.

## Run locally

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), GNU Make,
and Node.js 24 with npm. If you use nvm, run `nvm install` from the repo root.
The backend supports Python 3.14 and 3.15. uv defaults to Python 3.15.2, pinned in
`backend/.python-version`. To use Python 3.14, run `export UV_PYTHON=3.14` in the
backend terminal before setup and startup.

Install the locked dependencies and serve the app from the repo root:

```sh
make setup
make serve
```

`make serve` builds the frontend and serves it alongside the API. Open
[Scentfolio on port 8000](http://localhost:8000).

For hot reload, run `make dev-backend` and `make dev-frontend` in separate
terminals and open [Scentfolio on port 5173](http://localhost:5173). Vite sends
`/api` requests to [FastAPI on port 8000](http://localhost:8000/docs).

Run `make help` to list the available commands.

### Keep an existing collection

When updating an existing checkout, leave `backend/scentfolio.db` in place and
start the app as usual. Startup upgrades the SQLite schema in place. Your
scents, notes, and impressions carry over. Entries created before the Saved
section appear in Collection.

If your database lives elsewhere, run the launcher with its existing file path:

```sh
SCENTFOLIO_DB_URL="sqlite:////absolute/path/to/scentfolio.db" make serve
```

### Enable AI features

Create `backend/.env` from [the example](backend/.env.example) and choose a
provider for lookup, note enrichment, and family reclassification. Scentfolio
uses [Pydantic AI](https://pydantic.dev/docs/ai/) for model calls. Restart the
backend after editing the file.

| `SCENTFOLIO_LLM_PROVIDER` | Setup | Lookup |
| --- | --- | --- |
| `anthropic` (default) | Set `ANTHROPIC_API_KEY` or `SCENTFOLIO_LLM_API_KEY`. Optionally set `SCENTFOLIO_LLM_MODEL` to override the defaults. | Claude web search with source links. |
| `openai` | Set `OPENAI_API_KEY` or `SCENTFOLIO_LLM_API_KEY` and set `SCENTFOLIO_LLM_MODEL` to a model that supports Responses web search. | OpenAI web search with source links. |
| `openai-compatible` | Set `SCENTFOLIO_LLM_MODEL` to your provider's model ID and `SCENTFOLIO_LLM_API_KEY` to your key. The default OpenAI endpoint also accepts `OPENAI_API_KEY`. | Uses the model's knowledge. |

The Anthropic defaults are Claude Opus 5.5 for lookup and family
reclassification and Claude Haiku 5.5 for note enrichment.

For a compatible API other than OpenAI, set `SCENTFOLIO_LLM_BASE_URL` to its
API base, such as `https://generativelanguage.googleapis.com/v1beta/openai/` for
[Gemini](https://aistudio.google.com/docs/openai) or `http://localhost:11434/v1`
for [local Ollama](https://docs.ollama.com/api/openai-compatibility). Use a model
that supports Chat Completions. Leave the key blank for a local server that
accepts unauthenticated requests.

Lookup drafts without provider citations are marked low confidence and have
an empty source list.
You can browse and export your collection without configuring a provider.

## Check changes

From the repo root:

```sh
make check
```

Use `make format` to apply formatting, or `make test-backend` and
`make test-frontend` to run the suites individually. The backend tests use an
in-memory SQLite database and mock the AI calls.

See the [repo guide](docs/README.md) for where to make changes and the
[architecture](docs/architecture.md) for runtime and capacity decisions.
