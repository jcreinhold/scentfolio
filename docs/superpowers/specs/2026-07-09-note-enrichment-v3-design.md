# Note enrichment v3 — educational depth

## Context

The user wants the Notes Glossary to be a learning tool. Deeper, educational
content is needed: for naturals, how sourcing region changes the scent, where
it's most prized, and cultural background; for synthetics/accords (e.g.
aldehydes), a chemical-by-chemical breakdown of what each material smells like,
plus history. Additive to the existing enrichment (description, origin,
production, compounds, sourcing, proprietary_to, detail_version).

Decision (from brainstorming, recommended path): keep structured fields — expand
`sourcing` and `compounds` to be richer/longer, and add a new `history` field —
rather than one free-form "deep dive" blob.

## Data model + migration
Add to `Note` (via existing `ensure_schema` `_ADDED_COLUMNS["notes"]`):
- `history: Mapped[str]` (Text, default "").

## Versioning
`ENRICH_VERSION` → 3. All existing rows (< 3) are stale and re-enrich on the next
backfill. `notes_missing_enrichment` already selects `detail_version < ENRICH_VERSION`.

## Generation (`agent.py`)
Expand `NOTE_ENRICH_PROMPT` so the model returns richer content:
- `sourcing` (naturals): several sentences — how different origins/terroirs smell
  different, where the material is most prized, and cultural background.
- `compounds` (synthetics/accords): break down the key aroma-chemicals and what
  EACH smells like (e.g. aldehyde C-10 waxy-orange, C-11 green, C-12 soapy).
- `history` (new, either): origin/discovery story, a notable moment in perfumery,
  cultural significance.
Add `history` to the parsed output via `_clean_str`. Because content is longer,
raise `max_tokens` (~8000).

## Repository (`repository.py`)
`apply_note_enrichment` also sets `history` and (unchanged) stamps
`detail_version = ENRICH_VERSION`, preserving an existing description.

## Endpoint / batching (`main.py`)
- `GET /api/notes` and `GET /api/notes/{name}` include `history`.
- Use a smaller enrichment batch (ENRICH_CHUNK = 12) so longer responses fit the
  token budget.

## Frontend
- `api.ts`: note list + `getNote` types gain `history: string`.
- `NoteDetail.tsx`: add a "History" section (shown when populated). Sourcing and
  compounds already render full-length here.
- `Glossary.tsx`: no new card content; the richer sourcing/compounds stay clamped
  to their existing preview lines so cards remain scannable. (History is
  detail-page only.)

## Tests
- Backend: `enrich_notes` parses `history`; `apply_note_enrichment` sets it +
  stamps version; endpoint/GET include `history`.
- Frontend: NoteDetail renders the History section; Glossary card still renders
  (types updated).

## Verification
1. `cd backend && pytest -q`; `cd frontend && npx tsc … && npx vitest run && npm run build`.
2. Backend hot-reloads (ensure_schema adds `history`); `POST /api/notes/enrich-missing`
   re-enriches all (version 3) — confirm rose sourcing describes regional
   differences + culture; aldehydes compounds break down C-10/C-11/C-12; a
   `history` populated for several notes; descriptions unchanged; NoteDetail shows
   the History section.
