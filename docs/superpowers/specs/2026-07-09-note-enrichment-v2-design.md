# Note enrichment v2 — compounds, sourcing, proprietary house

## Context

Notes already carry `description`, `origin` (natural/synthetic/both), and
`production`. The user wants more depth in the Glossary: for synthetics, the key
chemical **compounds/materials**; for naturals, **sourcing / typical regions**;
and for captive molecules (e.g. Akigalawood → Givaudan) the **house/supplier it
is proprietary to**. Additive to the existing enrichment feature.

Decision (from brainstorming): three separate fields (compounds, sourcing,
proprietary_to) plus a `detail_version` so re-enrichment across the whole
collection is clean and unambiguous.

## Data model (`models.py`) + migration
Add to `Note` (all via the existing idempotent `ensure_schema` in `db.py` —
extend `_ADDED_COLUMNS["notes"]`):
- `compounds: str` (Text, default "") — key synthetic materials; blank for pure naturals.
- `sourcing: str` (Text, default "") — geographic sourcing for naturals; blank for pure synthetics.
- `proprietary_to: str` (String(80), default "") — captive molecule's house/supplier, else "".
- `detail_version: int` (default 0) — enrichment schema version.

## Versioned re-enrichment
`agent.py` defines `ENRICH_VERSION = 2`. A note "needs enrichment" when
`detail_version < ENRICH_VERSION`. All existing rows are effectively v1 (0), so
they re-process once; freshly re-enriched rows get stamped 2 and drop out. This
replaces the previous "origin == ''" missing check (ambiguous now that a natural
legitimately has empty compounds).

## Generation (`agent.py`)
Extend `enrich_notes` result per note to
`{description, origin, production, compounds, sourcing, proprietary_to}`. Prompt
additions: for synthetics/accords list the typical chemical compounds or
materials; for naturals give sourcing regions/origin; if the material is a known
captive/proprietary molecule, name the fragrance house or supplier it belongs to
(e.g. Akigalawood → Givaudan), else "". Validate `origin` as before; coerce
non-string fields to "".

## Repository (`repository.py`)
- `notes_missing_enrichment` → `WHERE Note.detail_version < ENRICH_VERSION`
  (import the constant from agent).
- `apply_note_enrichment` → also set compounds/sourcing/proprietary_to and stamp
  `detail_version = ENRICH_VERSION`; still preserve an existing description
  (only fill description when blank).

## Endpoint (`main.py`)
`POST /api/notes/enrich-missing` unchanged in shape. `GET /api/notes` and
`GET /api/notes/{name}` also return compounds, sourcing, proprietary_to.

## Frontend
- `api.ts`: notes list + `getNote` types gain `compounds`, `sourcing`,
  `proprietary_to`.
- `Glossary.tsx`: card adds a proprietary badge next to the origin chip when
  `proprietary_to` is set, and one compact labelled line — "Key compounds …"
  (synthetic) or "Sourcing …" (natural) when present. Button count unchanged
  (driven by the backend's version check → shows all stale notes).
- `NoteDetail.tsx`: add sections — "Key compounds", "Sourcing", and a
  "Proprietary to <house>" line — each shown only when populated.
- `styles.css`: `.note-proprietary` badge; reuse `.note-production` styling for
  the compounds/sourcing lines.

## Tests
- **Backend**: `enrich_notes` parses the wider object (compounds/sourcing/
  proprietary_to, non-strings → ""); `notes_missing_enrichment` treats v1 rows as
  stale and v2 rows as done; `apply_note_enrichment` sets the new fields, stamps
  version, preserves description; `ensure_schema` adds the new columns; endpoint +
  GET expose the fields.
- **Frontend**: Glossary shows the proprietary badge + a compounds/sourcing line;
  NoteDetail renders the new sections; existing enrich-button flow still works.

## Verification
1. `cd backend && pytest -q`; `cd frontend && npx tsc … && npx vitest run && npm run build`.
2. Backend hot-reloads (ensure_schema adds columns); `POST /api/notes/enrich-missing`
   re-enriches all (version bump) — confirm: ambroxan → compounds (ambrox/from
   sclareol); rose → sourcing (Grasse/Bulgaria/Turkey); Akigalawood →
   proprietary_to Givaudan; descriptions unchanged; Glossary + note page show the
   new detail in light/dark.
