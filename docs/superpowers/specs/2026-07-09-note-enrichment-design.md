# Note enrichment — origin & production facts

## Context

Notes now carry a Claude-generated `description`. The user wants the Glossary to
also show, per note: whether it's usually **natural / synthetic / both**, and an
interesting **production** fact (how a natural is harvested/extracted, or how a
synthetic or accord is constructed). Purely additive to the existing note-
description feature.

Decisions (from brainstorming): origin is a fixed-label chip
(natural/synthetic/both/unknown); the backfill **preserves existing descriptions**
and only fills the new fields.

## Data model (`models.py`)
Add to `Note`:
- `origin: Mapped[str]` = `mapped_column(String(20), default="")` — one of
  `natural` / `synthetic` / `both` / `""`.
- `production: Mapped[str]` = `mapped_column(Text, default="")`.

## Migration — idempotent additive `ensure_schema`
No migration tool exists and `create_all` won't ALTER an existing table, so add a
small self-healing step (in `db.py`, called from `deps.py` after `create_all`):
```
def ensure_schema(engine):
    with engine.begin() as conn:
        cols = {r[1] for r in conn.exec_driver_sql("PRAGMA table_info(notes)")}
        if "origin" not in cols:
            conn.exec_driver_sql("ALTER TABLE notes ADD COLUMN origin VARCHAR(20) DEFAULT ''")
        if "production" not in cols:
            conn.exec_driver_sql("ALTER TABLE notes ADD COLUMN production TEXT DEFAULT ''")
```
Fresh DBs already have the columns from the model, so this is a no-op there;
it only heals the existing `scentfolio.db`. SQLite-scoped (the app is SQLite).

## Generation (`agent.py`)
Replace `describe_notes` result shape (or add a richer sibling) so each note maps
to an object. Preferred: rename intent to **`enrich_notes(names) -> dict[name ->
{description, origin, production}]`** — one batched Haiku call per chunk. Prompt:
for each note return `{"description": 1-2 sentences, "origin": one of
natural|synthetic|both, "production": 1-2 sentences on how it's harvested (natural)
or constructed (synthetic/accord)}`. Keep only requested names; validate `origin`
against the set (else `""`); reuse `_isolate_json`; raise `LookupError` on bad JSON.

## Repository (`repository.py`)
- `notes_missing_enrichment(session)` — notes where `origin == ""` (targets all
  currently-unenriched notes, including the 170 that already have descriptions).
- `apply_note_enrichment(session, mapping)` — for each named note: set `origin`
  and `production`; set `description` **only if currently blank** (preserve
  existing). Return count updated.
- Keep the existing `notes_missing_description` / `apply_note_descriptions`?
  Superseded — replace their single call site (the endpoint) with the enrichment
  versions; remove the now-unused originals to avoid dead code.

## Endpoint (`main.py`)
- Repurpose `POST /api/notes/describe-missing` → `POST /api/notes/enrich-missing`
  (find `notes_missing_enrichment`, chunk ~25, call injected enricher, apply).
  Update `get_note_describer` → `get_note_enricher`. Returns `{"updated": N}`.
- `GET /api/notes` and `GET /api/notes/{name}` include `origin` and `production`.

## Frontend
- `api.ts`: notes list type + `getNote` return gain `origin: string`,
  `production: string`; rename `describeMissingNotes` → `enrichMissingNotes`.
- `Glossary.tsx`: card shows an origin chip (e.g. `NATURAL`) and, under the
  description, a short production line (line-clamped). Button counts notes with
  no `origin`, labelled "Enrich notes (N)".
- `NoteDetail.tsx`: add an origin line and a "How it's sourced" section with the
  full `production` text.
- `styles.css`: `.note-origin` chip; reuse `.note-desc` clamp for production.

## Tests
- **Backend**: `enrich_notes` parses the richer object, validates origin, drops
  unknowns; `apply_note_enrichment` preserves an existing description while
  setting origin/production; `ensure_schema` adds missing columns and is
  idempotent (run twice); endpoint updates + returns count (fake enricher);
  `GET /api/notes` includes the new fields.
- **Frontend**: Glossary renders origin chip + production; "Enrich notes (N)"
  counts notes lacking origin, calls `enrichMissingNotes`, refreshes.

## Verification
1. `cd backend && pytest -q`.
2. `cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx vitest run && npm run build`.
3. Backend hot-reloads (ensure_schema adds the columns to the live DB); `POST
   /api/notes/enrich-missing` → confirm notes gain sensible origin + production
   (e.g. bergamot → natural, cold-pressed peel; ambroxan → synthetic, from
   sclareol/clary sage); existing descriptions unchanged; Glossary shows chips +
   facts in light/dark.
