import asyncio

import pytest

from app import repository as repo
from app.agent import Draft
from app.ai_work import AIWork, ProviderBusy
from app.db import Base, make_engine, make_sessionmaker
from app.llm import LookupError
from app.schemas import NoteInput, PerfumeCreate, PerfumeUpdate


@pytest.fixture
def storage(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'ai-work.db'}")
    Base.metadata.create_all(engine)
    try:
        yield engine, make_sessionmaker(engine)
    finally:
        engine.dispose()


async def _draft(name):
    return Draft(perfume=PerfumeCreate(name=name))


def test_lookup_rejects_overload_and_releases_cancelled_capacity():
    async def run():
        work = AIWork(max_concurrent=2)
        entered = asyncio.Queue()
        finish = asyncio.Event()

        async def lookup(name):
            entered.put_nowait(name)
            await finish.wait()
            return await _draft(name)

        first = asyncio.create_task(work.lookup("A", lookup))
        second = asyncio.create_task(work.lookup("B", lookup))
        assert {await entered.get(), await entered.get()} == {"A", "B"}
        with pytest.raises(ProviderBusy):
            await work.lookup("C", lookup)
        assert entered.empty()

        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        third = asyncio.create_task(work.lookup("C", lookup))
        assert await entered.get() == "C"
        finish.set()
        assert (await second).perfume.name == "B"
        assert (await third).perfume.name == "C"

    asyncio.run(asyncio.wait_for(run(), timeout=5))


def test_lookup_deadline_releases_provider_capacity():
    async def run():
        work = AIWork(max_concurrent=1, timeout=0.01)

        async def stalled(_name):
            await asyncio.Event().wait()

        with pytest.raises(LookupError, match="timed out"):
            await work.lookup("A", stalled)
        assert (await work.lookup("B", _draft)).perfume.name == "B"

    asyncio.run(run())


def test_enrichment_closes_sessions_and_preserves_progress_after_provider_error(
    storage,
):
    engine, sessions = storage
    note_count = 13
    notes = [NoteInput(name=f"note {i:02}", tier="top") for i in range(note_count)]
    with sessions() as session:
        repo.create_perfume(session, PerfumeCreate(name="A", notes=notes))

    async def run():
        work = AIWork()

        async def enrich(names):
            assert engine.pool.checkedout() == 0
            if names == ["note 12"]:
                raise LookupError("Provider unavailable.")
            return {name: {"origin": "natural"} for name in names}

        report = await work.enrich_missing(sessions, enrich)
        assert report == {"updated": note_count - 1, "remaining": 1, "failed": 1}

        with pytest.raises(LookupError, match="Provider unavailable"):
            await work.enrich_missing(sessions, enrich)

    asyncio.run(run())
    with sessions() as session:
        assert [note.name for note in repo.notes_missing_enrichment(session)] == [
            "note 12"
        ]


def test_reclassification_reserves_lookup_capacity_and_preserves_manual_edits(storage):
    engine, sessions = storage
    with sessions() as session:
        perfume = repo.create_perfume(
            session, PerfumeCreate(name="A", scent_families=["Woody"])
        )

    def change_families():
        with sessions() as session:
            repo.update_perfume(
                session, perfume.id, PerfumeUpdate(scent_families=["Floral"])
            )

    async def run():
        work = AIWork(max_concurrent=2)
        entered = asyncio.Event()
        finish = asyncio.Event()

        async def classify(*_args):
            assert engine.pool.checkedout() == 0
            entered.set()
            await finish.wait()
            return ["Green"]

        pending = asyncio.create_task(work.reclassify(sessions, classify))
        await entered.wait()
        with pytest.raises(ProviderBusy):
            await work.reclassify(sessions, classify)
        assert (await work.lookup("B", _draft)).perfume.name == "B"
        await asyncio.to_thread(change_families)
        finish.set()
        assert await pending == {"updated": 0}

    asyncio.run(asyncio.wait_for(run(), timeout=5))
    with sessions() as session:
        assert repo.get_perfume(session, perfume.id).scent_families == ["Floral"]
