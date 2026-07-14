# "Saved" section — track fragrances not in the collection

## Context

The user wants a second section to peruse fragrances they don't own — ones they're
considering buying or are simply familiar with — with the SAME level of detail as
their collection. Cleanest approach: one data model, tagged by status, reusing the
entire existing pipeline (Claude lookup, notes, tiers, families, enrichment, cards,
detail page). No parallel system.

## Data model + migration
- `Perfume.status: str` (default `"collection"`). Values: `"collection"` | `"saved"`.
- Add via the idempotent `ensure_schema` migration: extend `_ADDED_COLUMNS` with
  `"perfumes": [("status", "VARCHAR(20) DEFAULT 'collection'")]`, so the existing
  72 perfumes stay in the collection.

## Schemas
- `Status = Literal["collection", "saved"]`.
- `PerfumeCreate.status: Status = "collection"`, `PerfumeOut.status: str`,
  `PerfumeUpdate.status: Status | None = None` (enables moving between sections).

## Repository / queries / endpoint
- `create_perfume` writes `status`; `_to_out` reads it; `update_perfume` sets it.
- `list_perfumes(session, status=None)` and `search_perfumes(..., status=None)`
  filter by status when provided.
- `GET /api/perfumes?status=collection|saved` threads the param through both the
  plain-list and search paths.
- Insights unchanged — they aggregate everything (owned + saved), per decision.

## Frontend
- `types.ts`: `Perfume.status: string`.
- `api.ts`: `listPerfumes` filter gains `status?`; `updatePerfume` patch gains `status`.
- `Collection.tsx`: takes a `status` prop (default `"collection"`); passes it to
  `listPerfumes`; header eyebrow/title/subtitle + empty-state text vary by status.
- `App.tsx`: new sidebar link "Saved"; route `/saved` → `<Collection status="saved"/>`,
  `/` → `<Collection status="collection"/>`.
- `Add.tsx`: a "Add to: Collection · Saved" toggle (destination) applied to the
  saved perfume; passed into `BatchAdd` so bulk adds honor it too. Default Collection.
- `BatchAdd.tsx`: accept a `status` prop; set it on each `createPerfume`.
- `PerfumeDetail.tsx`: show the status; a button to move — "Move to collection"
  (when saved) / "Move to saved" (when owned) via a `status` PATCH.

## Tests
- Backend: schema default/validation for status; `list_perfumes`/`search_perfumes`
  filter by status; create with status + move via PATCH; `ensure_schema` adds the
  `status` column to a legacy perfumes table.
- Frontend: `Collection` with `status="saved"` shows the saved header and requests
  that status; Add "Saved" destination sets status on create; PerfumeDetail move
  button flips status. Update the typed `p()` test helpers to include `status`.

## Verification
1. `cd backend && pytest -q`; `cd frontend && npx tsc … && npx vitest run && npm run build`.
2. Restart backend (ensure_schema adds `status`); add a fragrance to Saved, confirm
   it appears under /saved (not /), has full detail, and "Move to collection" moves
   it to /.
