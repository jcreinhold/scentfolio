# Scentfolio architecture

Scentfolio tracks one shared fragrance collection per instance. `make serve`
builds the React app and starts one FastAPI process on loopback. The browser
and API share an origin. In development, Vite proxies `/api` to FastAPI.
For network access, keep the server behind an authenticated boundary and
give its users access to the same collection. A service that hosts private
collections for different users needs account and data isolation.

## Request paths

| Area | Owner | Boundary |
| --- | --- | --- |
| Browser state | React views and `useRequest` | A read belongs to its route, filters, and page. Superseded reads are canceled. Writes use the server response or reload the affected data. |
| HTTP | `app/api.py`, `app/schemas.py` | The API validates parameters, maps errors, and returns plain responses. `app/main.py` wires the routes, serves the built UI, and owns startup and shutdown. |
| Storage | `app/repository.py`, `app/queries.py`, `app/db.py` | A short session loads or writes the data needed for one operation. The handler releases the connection before FastAPI validates the response. |
| Model calls | `app/ai_work.py`, `app/agent.py`, `app/llm.py` | The AI service owns admission, timeouts, batches, and apply rules. Prompt and provider details stay behind the Pydantic AI adapter. |

Collection and Saved filter and sort the whole match set before slicing it.
The browser asks for 40 rows. `GET /api/perfumes` accepts `limit` (up to 100),
`offset`, `sort`, and `direction`. Paged responses keep the JSON array and add
`X-Total-Count`. Calls without paging or sorting keep the full-list behavior.
Note detail returns 404 when the note is absent. The glossary gets
`needs_enrichment` from the server, which owns the enrichment version.
Concurrent manual changes to different fields compose. When two users edit
the same field, the last committed value wins.

On startup, the app opens the configured SQLite file, adds missing columns
and indexes in a serialized transaction, and keeps existing rows and IDs.
Fresh files use the same startup path. Scentfolio automatically enables
write-ahead logging on SQLite 3.51.3 and later. Older runtimes retain the
file's journal setting. Use a SQLite build with the WAL-reset fix if you
enable WAL yourself or open a file already using it. SQLite admits one writer
at a time. Keep the database and its sidecar files on local storage. Use
SQLite's backup API or close all connections before copying the file.
[SQLite write-ahead logging](https://www.sqlite.org/wal.html)

Lookup returns an unsaved draft. Bulk enrichment and classification first
read a snapshot, await the provider without a database connection, then
apply each completed batch. Classification checks that the stored families
still match the snapshot. Enrichment applies only to notes still on an older
detail version. Partial progress stays in SQLite and the response reports any
failures. Each provider call has a 120-second deadline.

The server admits four simultaneous provider calls by default, configurable
with the process environment variable `SCENTFOLIO_AI_CONCURRENCY`. Only one
bulk job runs at a time. Bulk classification leaves capacity for interactive
lookup when the limit allows. A lookup that arrives at capacity, or a second
bulk job, receives HTTP 503 with `Retry-After`. The limits apply to one process.
Keep one process per instance until there is a reason to coordinate limits
and maintenance across processes.

## Why this design

| Problem in the previous design | Decision |
| --- | --- |
| Startup and route code shared global database setup. Slow model calls held server threads and database connections. | Give initialization to the app lifespan and open sessions where the work happens. Use async provider calls with explicit admission limits. |
| List and insight queries repeatedly loaded related rows, and the browser downloaded and sorted the entire collection. | Load related rows in batches and page in SQL. Use indexed note lookups and purpose-built projections for insights. |
| Browser responses could land out of order. A failed optimistic write could restore data changed by another request. | Tie each read to its inputs, track writes by record, and refresh from confirmed state. Refresh similarity with the other family-dependent reports. |
| Slow reclassification could overwrite a manual change. The browser had its own idea of which notes were stale. | Check the stored snapshot when applying delayed writes and keep enrichment version policy in storage. |
| The main bundle loaded charts before anyone opened Insights. | Load the Insights route and chart library on demand. |

These decisions follow John Ousterhout's *A Philosophy of Software Design* on
deep modules, information hiding, and designing alternatives, and Rich
Hickey's *Simple Made Easy* on separating values, effects, and time.
The app keeps one deployable process and a single-file database. That keeps
setup and upgrades small and lets runtime measurements guide added services.

## Capacity and next limits

Use about 100 simultaneous browser clients as an initial test workload.
Measure the request mix, payload sizes, p95 latency, SQLite lock errors,
and provider rejections separately. HTTP concurrency and provider concurrency
have separate budgets. Use a loopback mock for AI integration and load tests.

One local Uvicorn process served 500 requests from 100 concurrent clients
with a scratch database of 240 fragrances. Each client listed the collection,
read a detail, read a note or created a fragrance, searched or ran similarity,
and checked health. All requests succeeded in each run.

| Run | List p95 | Total time | Response bodies |
| --- | ---: | ---: | ---: |
| Previous version, full list and search | 13.3 s | 18.7 s | 15.2 MB |
| Current version, full list and search | 9.8 s | 11.6 s | 15.2 MB |
| Current browser page size (40) | 2.7 s | 5.7 s | 4.9 MB |

In a separate burst of 100 lookups, a delayed loopback provider held four
requests. The other 96 received HTTP 503 with `Retry-After`. Health requests
served during the delay took 1.2–3.1 ms.

Exact similarity still checks every pair. It holds only the top results and
releases the database connection before scoring. If large collections make
that endpoint a bottleneck, measure a cached or precomputed report keyed to
collection changes. Consider a server database when sustained write contention
or multi-host deployment calls for it. Move maintenance to a durable worker
if jobs need to survive restarts or run independently of an HTTP request.
