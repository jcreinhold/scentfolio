# Similar-pairs redesign — tier-aware, family-weighted similarity

## Context

The Insights "most similar pairs" ranks by raw shared-note COUNT
(`queries.similar_pairs`), which structurally favors note-heavy perfumes: a
fragrance with many notes (e.g. Ramune) shares common base notes (musk, amber,
woods) with almost everything and gets paired with wildly different scents. We
want a normalized, more meaningful similarity that matches notes tier-to-tier and
factors in scent family.

## Algorithm (`queries.similar_pairs`)

For each unordered pair, compute Jaccard indices (|∩| / |∪|, 0 when both empty):
- `topJ` — notes in the `top` tier of each
- `heartJ` — notes in the `heart` tier
- `baseJ` — notes in the `base` tier
- `familyJ` — scent-family tag sets

Composite score in [0,1]:
`0.30·topJ + 0.30·heartJ + 0.15·baseJ + 0.25·familyJ`
(base deliberately down-weighted since base notes are near-universal).

Jaccard normalization removes the note-count bias; tier-matching means a note
only counts as shared if it plays the same role in both perfumes.

Return, sorted by score desc, the top N (default 15), dropping score ≤ 0:
```
{ a, b, score,                       # score rounded to 3dp
  shared_families: [...],
  shared_top: [...], shared_heart: [...], shared_base: [...] }
```
Drop the old `shared`/`count` keys.

Helpers: `_tiered_notes(p) -> {tier: set[name]}`, `_families(p) -> set[str]`
(split the comma-joined `scent_family`), `_jaccard(a, b)`.

## Frontend (`Insights.tsx`, `api.ts`)
- `insightSimilar` return type → the new shape.
- Render each pair as a row: "A ↔ B" with a **match %** (`round(score*100)`), and a
  breakdown line of shared families + shared notes grouped by tier (only the
  groups that have shared items). Section label → "Most similar pairs".

## Tests
- `test_queries`: seed two perfumes sharing a TOP note and one family; assert the
  top pair's `shared_top` and `shared_families` are right and `score` is in
  (0,1); assert a perfume that only shares diluted base notes ranks below a
  same-tier/same-family match (the anti-Ramune case).
- `test_api`: `/api/insights/similar` still 200.
- Frontend `Insights.test`: update the `insightSimilar` mock to the new shape;
  assert the two names and a match % render.

## Verification
1. `cd backend && pytest -q`; `cd frontend && npx tsc … && npx vitest run && npm run build`.
2. Live Insights: confirm the top pairs are genuinely alike (shared top/heart +
   family), and that a note-heavy perfume no longer dominates via base overlap.
