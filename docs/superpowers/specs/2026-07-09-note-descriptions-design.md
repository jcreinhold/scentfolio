# Note descriptions — design

## Context

The `Note` model has a `description` column, but it is never populated —
`repository._get_or_create_note` only sets `name` and `family`. As a result the
Note Glossary shows only name + family, and the Note detail page always reads
"No description yet." The user wants notes to carry a short "what it smells like"
description.

Decisions (from brainstorming): descriptions are **Claude-generated and cached**
in the DB, and populated via a **bulk backfill** the user triggers, so cost is
explicit and the Glossary fills immediately. New notes added later simply appear
in the "missing" count and are filled by the same backfill.

## Backend

### `agent.py` — `describe_notes(names, client=None) -> dict[str, str]`
- No web search needed (a note's scent is general knowledge), so a plain
  `messages.create` with **`claude-haiku-4-5-20251001`** (cheap/fast) and a small
  `max_tokens`.
- System prompt: fragrance expert; for each note name, write a concise 1–2
  sentence olfactory description; return ONLY a JSON object mapping each exact
  input name → description.
- Reuse the existing `_isolate_json` helper to extract the JSON. Return only
  entries whose key was in `names`; missing keys are simply skipped (non-fatal).
- Raises `LookupError` on unparseable output (consistent with `lookup`).

### `repository.py`
- `notes_missing_description(session) -> list[Note]` — notes where
  `description == ""`.
- `apply_note_descriptions(session, mapping: dict[str, str]) -> int` — set
  `description` for each named note (normalized lowercase), commit, return count
  updated.

### `main.py`
- `POST /api/notes/describe-missing` → gather missing notes, chunk names (~25),
  call the injected describer per chunk, merge, `apply_note_descriptions`, return
  `{"updated": N}`. Describer injected via `get_note_describer` (Depends), mirroring
  `get_lookup`, for testability.
- `GET /api/notes` now includes `description` in each item.

## Frontend

### `api.ts`
- `listNotes()` return type gains `description: string`.
- `describeMissingNotes(): Promise<{ updated: number }>` → POST the endpoint.

### `Glossary.tsx`
- Each note card renders its `description` (truncated with CSS line-clamp) below
  the family; blank descriptions show nothing (or a faint placeholder).
- Compute `missing = notes.filter(n => !n.description).length`. When `missing > 0`,
  show a header button "Generate descriptions (N)". Click → `describeMissingNotes()`
  (button shows a working state), then re-fetch `listNotes()` to refresh.

### `NoteDetail.tsx`
- No change needed — it already renders `description` (falls back to "No
  description yet."); it lights up once populated.

## Error handling
- Endpoint: if the describer fails on a chunk, that chunk is skipped (logged),
  others still apply; the response reports how many were actually updated.
- Frontend: on failure, restore the button and surface a brief error; nothing is
  partially rendered.

## Testing
- **Backend**
  - `agent.describe_notes`: fake client returning fenced/plain JSON → correct map;
    extra/missing keys handled; bad JSON raises `LookupError`.
  - `repository`: `notes_missing_description` finds only blank ones;
    `apply_note_descriptions` sets + counts, ignores unknown names.
  - `main`: `POST /api/notes/describe-missing` with an injected fake describer
    updates the right notes and returns the count; `GET /api/notes` includes
    `description`.
- **Frontend**
  - `Glossary`: renders a description; shows "Generate descriptions (N)" when some
    are missing; clicking calls `describeMissingNotes` and re-fetches.

## Verification
1. Backend: `cd backend && pytest -q`.
2. Frontend: `cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx vitest run && npm run build`.
3. Dev server (backend + `localhost:5173`): open Glossary → click "Generate
   descriptions (N)" → cards fill with blurbs; open a note → detail shows the same
   description; reload → descriptions persist (DB-cached); the missing count drops
   to 0.
