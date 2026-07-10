# Multi-family scent classification — design

## Context

Perfumes carry a single `scent_family` (one string from an 11-value list), and
several are miscategorized (e.g. Milk → Woody but really Gourmand; Pony Boy →
Fresh but more Floral/Fruity; Dandelion Butter → Floral but more Gourmand/Green).
A perfume often spans multiple families. The user wants perfumes to hold
**multiple family tags** drawn from a vocabulary aligned with modern groupings,
and wants the existing 33-perfume collection **re-classified by research**.

Decisions (from brainstorming):
- Vocabulary = current 11 **plus Fruity and Green** (13 total): Citrus, Floral,
  Fruity, Green, Woody, Oriental, Fresh, Aromatic, Fougere, Chypre, Gourmand,
  Leather, Other.
- Re-classify all 33 now via a Claude web-search backfill (~33 calls, approved).

## Storage — mirror the `formats` pattern (no schema migration)

The DB has no migration tooling (schema via `create_all`, which won't ALTER an
existing table). `formats` already solves the exact same "list stored on one
row" problem: `Perfume.formats` is a comma-joined `String`, exposed as
`formats: list[str]`, joined on write / split on read.

Do the same for families **without renaming the DB column**:
- Keep column `Perfume.scent_family` (`String`), now holding a comma-joined list.
- API/schema field becomes `scent_families: list[str]`.
- `repository.create_perfume`: `scent_family = ",".join(data.scent_families)`.
- `repository._to_out`: `scent_families = p.scent_family.split(",") if p.scent_family else []`.
- Existing single-value rows split into a one-element list → backward-compatible.

Follow `formats`' exact join/split idiom in `repository.py` so the two are
consistent (check current `formats` handling and match it).

## Schemas (`schemas.py`)
- `Family` literal: add `"Fruity"`, `"Green"`.
- `PerfumeCreate.scent_families: list[Family] = Field(default_factory=list)`
  (replaces `scent_family`).
- `PerfumeOut.scent_families: list[str]`.
- `PerfumeUpdate.scent_families: list[Family] | None = None` (enables manual
  correction + reused by reclassify).

## Agent (`agent.py`)
- `VALID_FAMILIES`: add Fruity, Green.
- `SYSTEM_PROMPT`: return `scent_families` — a JSON array of 1–3 values from the
  vocabulary (was single `scent_family`).
- `extract_draft`: read `scent_families`, keep only valid values, dedupe,
  default `[]`. (Replaces the single-value → "Other" coercion.)
- New `classify_families(name, house, notes, client=None) -> list[str]`:
  Claude web-search call; system prompt asks it to research the perfume's modern
  scent grouping (main accords) and return ONLY a JSON array of 1–3 families from
  the vocabulary. Reuse `_isolate_json`; keep only valid values; raise
  `LookupError` on unparseable output. `notes` passed as context (names + tiers).

## Repository (`repository.py`)
- Join/split `scent_families` as above.
- `set_scent_families(session, perfume_id, families) -> bool` for the reclassify
  endpoint (writes comma-joined, commits).

## Queries (`queries.py`)
- `family_breakdown`: families are now multi-valued per row, so SQL GROUP BY no
  longer works. Fetch all non-empty `scent_family` strings, split on comma,
  count each tag in Python, return `[(family, count)]` sorted by count desc.
- `search_perfumes(family=...)`: match any perfume whose list contains `family`.
  Use the same delimiter-safe match `fmt` filtering uses (mirror it); the 13-value
  vocabulary has no name that is a substring of another, so a `LIKE '%family%'`
  is safe if that is the existing `fmt` idiom.

## Endpoints (`main.py`)
- `POST /api/perfumes/reclassify`: for each perfume, call the injected classifier
  with (name, house, notes), `set_scent_families`; run concurrently
  (ThreadPoolExecutor, ~4 workers). Return `{"updated": N}`. Classifier injected
  via `get_family_classifier` (Depends), mirroring `get_lookup`.
- `list_perfumes` / `insight_families` unchanged in signature; they ride on the
  updated queries.

## Frontend
- `types.ts`: `Perfume.scent_families: string[]` (replaces `scent_family`).
- `Collection.tsx`: add Fruity, Green to `FAMILIES`; filter dropdown unchanged
  (single-select, any-match server-side).
- `PerfumeCard.tsx`: render `scent_families` as small family chips (new — cards
  currently show no family), placed under the house/perfumer line.
- `PerfumeDetail.tsx`: render family tags as chips in the header (was single
  string in subtitle).
- `PerfumeTable.tsx`: Family column joins tags (`" · "`); sort accessor uses the
  joined lowercased string (`lib/perfumeSort.ts`).
- `Insights.tsx`: add a "Re-classify families" button that calls the reclassify
  endpoint then refreshes the chart; chart itself unchanged.
- `api.ts`: `reclassifyPerfumes(): Promise<{updated:number}>`; family filter and
  `insightFamilies` shapes unchanged.

## Tests
- **Backend**: update fixtures using `scent_family=` → `scent_families=[...]`
  (`test_models`, `test_schemas`, `test_repository`, `test_lookup_api`,
  `test_queries`, `test_api`). Replace the "unknown family → Other" agent test
  with array validation (invalid values dropped). Add: `classify_families`
  parsing (fake client), reclassify endpoint (fake classifier updates tags &
  returns count), `family_breakdown` counting across multi-tag rows, any-match
  family filter.
- **Frontend**: update fixtures to `scent_families` arrays; assert card/detail
  render family chips; Insights reclassify button calls `reclassifyPerfumes` and
  refreshes.

## Verification
1. Backend: `cd backend && pytest -q`.
2. Frontend: `cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx vitest run && npm run build`.
3. Restart backend (already running with `--reload`, so hot-reloads), then
   `POST /api/perfumes/reclassify`; confirm the cited perfumes get sensible
   multi-tags (Milk → Gourmand; Pony Boy → Floral/Fruity; Dandelion Butter →
   Gourmand/Green/…); check Insights counts sum across tags; check the Collection
   family filter returns any perfume carrying the tag; confirm cards/detail/table
   show the chips in light + dark mode.
