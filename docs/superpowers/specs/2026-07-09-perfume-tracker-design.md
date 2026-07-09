# Perfume Tracker ("Scentfolio") — Design

**Date:** 2026-07-09
**Status:** Approved design, ready for implementation planning

## Overview

A local-first web app for cataloguing a personal perfume collection and learning
about fragrance notes. The user types a perfume name; an AI agent searches the web
(Fragrantica, brand sites, and other sources) and extracts structured facts — top /
heart / base notes, perfumer, house, release year, scent family, and a description.
The user confirms/edits, adds their own impressions, and the perfume joins a
searchable, cross-linked collection.

The app is built to run locally on macOS now, with a clean path to being hosted
later (real database, backend/frontend split).

## Goals

- **Effortless capture:** type a name, get accurate structured data back with minimal
  manual entry.
- **Understand the collection:** see the shape of what you own — dominant notes,
  scent families, overlaps between fragrances.
- **Learn scents:** notes are first-class, clickable objects with descriptions and
  links to every perfume that features them.

## Non-Goals (YAGNI)

- No ratings, ownership status (owned/wishlist/sold), price, or purchase-date tracking.
- No multi-user accounts or auth (single user, local).
- No mobile-native app. (Hosting the web app for phone access is a possible future
  step, explicitly out of scope for v1.)
- No direct scraping of Fragrantica (bot-protected, ToS issues) — lookups go through
  the AI agent's web search.

## Architecture

Three units with clear boundaries:

1. **Backend API — Python + FastAPI.**
   - Serves a JSON API and owns all business logic.
   - Talks to the Claude API (with the built-in web search tool) for perfume lookups.
   - Persists to **SQLite** via SQLAlchemy (schema written to allow a later swap to
     Postgres when hosted).

2. **Lookup agent (backend module).**
   - Given a perfume name (optionally + house), calls the Claude API with web search,
     instructing it to return a **structured JSON object** (notes by tier, perfumer,
     house, year, family, description, source URLs).
   - Uses a strict output schema; validates before returning to the caller.
   - Returns a *draft* the user confirms — never writes to the DB directly.

3. **Frontend — React + Vite.**
   - Single-page app consuming the JSON API.
   - Three areas: Collection, Insights, Note Glossary.
   - Visual insight views (charts, groupings) live here.

Data flow for adding a perfume:

```
user types name → POST /lookup → agent (Claude + web search)
    → draft JSON returned to UI → user confirms/edits
    → POST /perfumes → validated + saved to SQLite → appears in Collection
```

## Data Model

**Perfume**
- `id`
- `name`
- `house` (brand)
- `perfumer` (nullable)
- `year` (nullable)
- `scent_family` (primary classification, e.g. "Woody Aromatic"; nullable)
- `description` (auto-pulled official/summary text)
- `my_impressions` (free text, user-authored)
- `formats` (set of: `full`, `travel`, `sample` — zero or more)
- `source_urls` (where the agent got the data, for trust/verification)
- `created_at`

**Note**
- `id`
- `name` (canonical, deduplicated — e.g. "bergamot")
- `family` (the note's own family, e.g. "Citrus"; nullable)
- `description` (what it smells like — auto-pulled/generated, editable)

**PerfumeNote** (join)
- `perfume_id`
- `note_id`
- `tier` (`top` | `heart` | `base`)

Notes are normalized (shared across perfumes) so the glossary and
"which perfumes have this note" queries are direct joins. The agent's free-text notes
are matched to existing `Note` rows by normalized name, creating new ones as needed.

## Features

### Collection (home)
- Grid of perfume cards: name, house, year, format badge(s), a couple of notes.
- Persistent **"Add a perfume by name…"** bar triggering the lookup flow.
- **Search box matches names OR notes.** Filter chips narrow by **scent family** and
  **format**.

### Add / Lookup flow
- Type name → agent lookup → **confirmation screen** showing the drafted fields and
  source URLs → user edits anything → save.
- Handles the case where the agent is unsure or finds conflicting data (see Error
  Handling).

### Perfume detail
- Note pyramid (top / heart / base), each note clickable → glossary.
- Perfumer, house, year, scent family, auto-pulled description.
- Editable format toggles (Full / Travel / Sample, multi-select).
- **My impressions** free-text field.

### Insights
- **Note frequency map:** most common notes across the collection.
- **Scent family grouping:** collection broken down by family.
- **Similarity & overlap:** find perfumes sharing notes; compare any two side by side.
- (Bonus, low-cost given the data) format breakdown, e.g. samples vs. full bottles.

### Note Glossary
- Browsable list of every note in the collection.
- Note detail: family, "what it smells like" description, and every perfume in the
  collection featuring it (with the tier it appears in).

## Error Handling

- **Lookup failure / no results:** show a clear message; let the user save a
  minimal manual entry (name + house) and fill in details later.
- **Low-confidence or conflicting data:** the agent returns a confidence signal and
  source URLs; the confirmation screen flags uncertain fields so the user can verify
  against the linked sources before saving. Nothing is saved without user confirmation.
- **API key missing/invalid:** app runs and browses existing data; lookups show a
  friendly "add your Claude API key" prompt. Key stored in a local `.env` (gitignored).
- **Duplicate perfume:** on add, warn if a perfume with the same name+house already
  exists.

## Testing

- **Backend unit tests:** data model + note-normalization logic, API endpoints
  (CRUD, search/filter), insight aggregations — using a temp SQLite DB.
- **Agent tests:** the lookup module is tested against **recorded/mocked** Claude
  responses (fixtures), so tests are deterministic and don't hit the network or spend
  tokens. Schema validation is tested with malformed responses.
- **Frontend:** component tests for the key views (collection/search, detail,
  glossary) against a mocked API.
- A small end-to-end happy path (add → appears in collection → searchable by note) is
  valuable but can be added after the core is in place.

## Tech Stack Summary

- **Backend:** Python, FastAPI, SQLAlchemy, SQLite, Anthropic SDK (Claude + web search tool).
- **Frontend:** React, Vite; a lightweight chart lib (e.g. Recharts) for insights.
- **Config:** `.env` for the Claude API key (gitignored).

## Future (explicitly deferred)

- Hosting for phone access (SQLite → Postgres, deploy).
- Optional offline seed from a public fragrance dataset as a fallback cache.
- Additional personal metadata (ratings, wear log) if desired later.
