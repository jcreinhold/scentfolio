# Batch add — design

## Problem

Adding perfumes one at a time is too slow for a large collection. Each add
requires (1) typing a name, (2) waiting a couple seconds for the Claude
web-search lookup, and (3) approving/saving that single result. The lookup
latency and the per-item approval are the two bottlenecks.

## Goal

Let the user add many perfumes in one pass: paste a list of names, look them all
up concurrently, review the results as a single checklist, and save the kept
ones in one action.

## Non-goals

- No inline text editing of looked-up results (keep/drop only). A wrong lookup
  is dropped and re-added via Single mode.
- No per-row format selection. Batch-added perfumes have empty formats, set
  later on each perfume's detail page.
- No backend/endpoint changes. Reuse existing `/api/lookup`,
  `/api/perfumes/check-duplicate`, and `POST /api/perfumes`.

## User flow

1. On the Add page, a mode toggle switches between **Single** (existing form,
   unchanged) and **Batch**.
2. Batch mode shows a textarea (one perfume name per line) and a "Look up all"
   button. Blank lines and duplicate lines are ignored/de-duplicated.
3. On submit, names are looked up concurrently (see Concurrency). Results stream
   into a review list as each resolves.
4. Each row reflects its state:
   - **Loading** — spinner row.
   - **Success** — checked by default; shows `name · house`, a confidence badge,
     a short notes preview, and a ⚠️ flag if `check-duplicate` returns true.
   - **Failed** — shown in red with the error; checkbox disabled (nothing to save).
5. A header shows "Save N selected". The user unchecks any unwanted rows.
6. "Save all" creates the checked perfumes via `POST /api/perfumes`, concurrently.
   On completion it reports "Added N perfumes" with a link to the collection.
   Rows that fail to save remain listed with their error for a manual retry.

## Concurrency

Both the lookup phase and the save phase run through a small client-side
concurrency pool capped at **4 in flight**. This keeps a large paste (e.g. 40
names) from firing 40 simultaneous Claude web-search calls and tripping API rate
limits, while still being far faster than sequential.

A reusable helper `mapPool(items, limit, fn)` in `api.ts` runs `fn` over `items`
with at most `limit` concurrent, preserving result order and capturing per-item
success/error so one failure doesn't sink the batch.

## Components

- **`api.ts`** — add `mapPool` concurrency helper. No new endpoints.
- **`BatchAdd.tsx`** (new) — the batch textarea, lookup orchestration, review
  checklist, and save-all action. Owns the per-item state machine
  (`pending → loading → success | error`, plus `kept` and `saved` flags).
- **`Add.tsx`** — add the Single/Batch mode toggle; render `<BatchAdd />` in
  batch mode. Single-add code is otherwise untouched.

## Per-item state

```
{
  name: string,            // the input line
  status: "loading" | "success" | "error",
  draft?: Draft,           // from /api/lookup on success
  duplicate?: boolean,     // from check-duplicate
  error?: string,          // lookup or save error message
  kept: boolean,           // checkbox; defaults true on success, false/disabled on error
  saveState?: "saving" | "saved" | "error",
}
```

## Error handling

- A single lookup failure marks only that row `error`; the rest proceed.
- Duplicate-check failure is non-fatal — the row still saves, just without a flag
  (mirrors current single-add behavior).
- A save failure marks only that row; already-saved rows are not re-created on a
  retry (saved rows are excluded from subsequent "Save all").

## Testing

- `mapPool`: respects the concurrency cap, preserves order, isolates per-item
  errors.
- `BatchAdd`: parses/de-dupes the textarea; renders success/loading/error rows;
  save-all calls `createPerfume` once per kept row and reports the count;
  unchecked rows are not saved; failed-lookup rows can't be saved.
