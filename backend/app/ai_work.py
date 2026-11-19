"""Run provider work independently of the threads that serve SQLite requests."""

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from itertools import batched

from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app import repository as repo
from app.agent import Draft
from app.llm import LookupError
from app.schemas import PerfumeOut

type SessionFactory = Callable[[], Session]
type Lookup = Callable[[str], Awaitable[Draft]]
type Enrichment = dict[str, dict[str, str]]
type Enrich = Callable[[list[str]], Awaitable[Enrichment]]
type Classify = Callable[[str, str, list[str]], Awaitable[list[str]]]

# A full note entry is long. Small batches also make partial work durable.
_ENRICH_BATCH_SIZE = 12
_CLASSIFY_BATCH_SIZE = 4


class ProviderBusy(Exception):
    """The bounded service cannot admit another request."""


@dataclass
class _Progress:
    """Report partial results and raise the first error if no batch answered."""

    updated: int = 0
    failed: int = 0
    answered: bool = False
    first_error: LookupError | None = None

    def record_failure(self, count: int, error: LookupError) -> None:
        self.failed += count
        self.first_error = self.first_error or error

    def response(self, **fields: int) -> dict[str, int]:
        if self.first_error is not None and not self.answered:
            raise self.first_error
        result = {"updated": self.updated, **fields}
        if self.failed:
            result["failed"] = self.failed
        return result


def _pending_notes(sessions: SessionFactory) -> list[str]:
    with sessions() as session:
        return [note.name for note in repo.notes_missing_enrichment(session)]


def _apply_notes(sessions: SessionFactory, output: Enrichment) -> int:
    with sessions() as session:
        return repo.apply_note_enrichment(session, output)


def _perfumes(sessions: SessionFactory) -> list[PerfumeOut]:
    with sessions() as session:
        return repo.list_perfumes(session)


def _apply_families(
    sessions: SessionFactory, rows: list[tuple[PerfumeOut, list[str]]]
) -> int:
    with sessions() as session:
        return sum(
            repo.set_scent_families(
                session, perfume.id, families, expected_families=perfume.scent_families
            )
            for perfume, families in rows
        )


class AIWork:
    """Limit provider calls and allow one bulk job at a time per app.

    Set max_concurrent for the shared call limit and timeout for the
    per-call deadline in seconds. SQLite sessions close before provider waits.
    """

    def __init__(self, max_concurrent: int = 4, timeout: float = 120):
        if max_concurrent < 1 or timeout <= 0:
            raise ValueError("AI concurrency and timeout must be positive.")
        self._provider = asyncio.Semaphore(max_concurrent)
        self._maintenance = asyncio.Lock()
        self._timeout = timeout
        # Leave a provider slot for interactive lookups whenever there is capacity.
        self._classify_batch_size = max(
            1, min(_CLASSIFY_BATCH_SIZE, max_concurrent - 1)
        )

    async def _call[T, **P](
        self, callback: Callable[P, Awaitable[T]], *args: P.args, **kwargs: P.kwargs
    ) -> T:
        async with self._provider:
            try:
                async with asyncio.timeout(self._timeout):
                    return await callback(*args, **kwargs)
            except TimeoutError:
                raise LookupError("The language model request timed out.") from None

    @asynccontextmanager
    async def _bulk(self):
        if self._maintenance.locked():
            raise ProviderBusy("Collection maintenance is already running.")
        async with self._maintenance:
            yield

    async def lookup(self, name: str, callback: Lookup) -> Draft:
        """Return an unsaved draft or raise ProviderBusy when all slots are in use."""
        if self._provider.locked():
            raise ProviderBusy("AI lookup is busy. Try again shortly.")
        return await self._call(callback, name)

    async def enrich_missing(
        self, sessions: SessionFactory, callback: Enrich
    ) -> dict[str, int]:
        """Enrich stale notes and commit updates as each batch returns.

        Report updated and remaining notes, plus failures when present.
        Raise the first lookup error if every attempted batch fails.
        """
        async with self._bulk():
            names = await run_in_threadpool(_pending_notes, sessions)
            progress = _Progress()
            for batch in batched(names, _ENRICH_BATCH_SIZE, strict=False):
                try:
                    output = await self._call(callback, list(batch))
                    if not output:
                        raise LookupError(
                            "The language model returned no note details."
                        )
                except LookupError as error:
                    progress.record_failure(len(batch), error)
                    continue
                progress.answered = True
                progress.failed += sum(name not in output for name in batch)
                progress.updated += await run_in_threadpool(
                    _apply_notes, sessions, output
                )
            remaining = (
                await run_in_threadpool(_pending_notes, sessions) if names else []
            )
            return progress.response(remaining=len(remaining))

    async def _classify(
        self, perfume: PerfumeOut, callback: Classify
    ) -> list[str] | LookupError:
        try:
            families = await self._call(
                callback,
                perfume.name,
                perfume.house,
                [note.name for note in perfume.notes],
            )
            if families:
                return families
            return LookupError("The language model returned no fragrance families.")
        except LookupError as error:
            return error

    async def reclassify(
        self, sessions: SessionFactory, callback: Classify
    ) -> dict[str, int]:
        """Classify snapshots and commit results whose stored families still match.

        Report applied updates and any provider failures. Raise the first
        lookup error if every attempted classification fails.
        """
        async with self._bulk():
            perfumes = await run_in_threadpool(_perfumes, sessions)
            progress = _Progress()
            for batch in batched(perfumes, self._classify_batch_size, strict=False):
                async with asyncio.TaskGroup() as group:
                    tasks = [
                        group.create_task(self._classify(perfume, callback))
                        for perfume in batch
                    ]
                rows = []
                for perfume, task in zip(batch, tasks, strict=True):
                    if isinstance(result := task.result(), LookupError):
                        progress.record_failure(1, result)
                    else:
                        progress.answered = True
                        rows.append((perfume, result))
                if rows:
                    progress.updated += await run_in_threadpool(
                        _apply_families, sessions, rows
                    )
            return progress.response()
