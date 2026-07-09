from app import repository as repo
from app.schemas import PerfumeCreate, NoteInput

def _sample(name="Sauvage", house="Dior"):
    return PerfumeCreate(name=name, house=house, scent_family="Fresh",
                         formats=["full"],
                         notes=[NoteInput(name="Bergamot", tier="top", family="Citrus"),
                                NoteInput(name="ambroxan", tier="base")])

def test_create_normalizes_and_dedupes_notes(session):
    repo.create_perfume(session, _sample())
    repo.create_perfume(session, _sample(name="Homme", house="Dior"))
    # "Bergamot" and "bergamot" should be ONE note row (normalized lowercase)
    all_notes = repo.list_notes(session)
    names = [n.name for n in all_notes]
    assert names.count("bergamot") == 1

def test_get_perfume_returns_notes_with_tier(session):
    created = repo.create_perfume(session, _sample())
    got = repo.get_perfume(session, created.id)
    tiers = {n.name: n.tier for n in got.notes}
    assert tiers["bergamot"] == "top"
    assert tiers["ambroxan"] == "base"

def test_find_perfumes_by_note(session):
    repo.create_perfume(session, _sample())
    results = repo.perfumes_with_note(session, "bergamot")
    assert [p.name for p in results] == ["Sauvage"]
