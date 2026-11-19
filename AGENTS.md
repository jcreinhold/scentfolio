# Scentfolio

Scentfolio is a local-first fragrance tracker. One app instance owns one shared
collection in SQLite. Read [the architecture](docs/architecture.md) before
changing storage, request lifecycles, or provider work.

## Work in order

- Use the agreed plan as the work queue. Check prerequisites and file owners
  before assigning work, then record the owner and next check. Judge progress
  by the actual diff and results. Record changes in order and give the reason
  for each.
- Use plain, short words and active voice. Cut filler, jargon, and stock
  phrases. Put clarity first. Keep durable design decisions in the architecture
  guide and temporary plans in the task.
- Use `make setup` for a fresh checkout. Run `make check` and the checks in the
  plan before marking work complete. For serving changes, run `make serve` and
  check a deep-link refresh and an API request.
- Fix valid lint findings. Use a narrow test-only exception when a fix would
  obscure the assertion. Keep formatting and lint checks in place.

## Design

- Give each change one owner. Keep HTTP contracts in the API, query and write
  semantics in the repository, and provider limits in the AI service. Prefer
  a small interface that handles the common case over thin forwarding layers.
- Separate values from effects. Pass detached snapshots across provider waits.
  Open SQLite sessions inside each short read or write phase and close them
  before making a model call. Apply delayed results only while their inputs
  still match.
- Keep browser state tied to its request. Cancel superseded reads, keep loading
  and failure explicit, and reconcile edits with the server's response. Apply
  filters and sort to the full matching set before paging.
- Keep existing SQLite files usable. Use additive, repeatable schema changes
  and verify a legacy database in a scratch copy. Use a local mock for provider
  tests, including load and end-to-end checks.
- Measure query counts, response size, and latency before adding a cache,
  worker service, or new dependency. Compare alternatives at the scale and
  workload that actually matter.
