from app import repository as repo
from app.schemas import PerfumeCreate, NoteInput

def _sample(name="Sauvage", house="Dior"):
    return PerfumeCreate(name=name, house=house, scent_families=["Fresh"],
                         formats=["full"],
                         notes=[NoteInput(name="Bergamot", tier="top", family="Citrus"),
                                NoteInput(name="ambroxan", tier="base")])

def test_scent_families_round_trip_multi(session):
    created = repo.create_perfume(session, PerfumeCreate(
        name="Milk", house="Snif", scent_families=["Gourmand", "Woody"], notes=[]))
    assert repo.get_perfume(session, created.id).scent_families == ["Gourmand", "Woody"]

def test_set_scent_families_overwrites(session):
    created = repo.create_perfume(session, _sample())  # ["Fresh"]
    assert repo.set_scent_families(session, created.id, ["Gourmand", "Green"]) is True
    assert repo.get_perfume(session, created.id).scent_families == ["Gourmand", "Green"]

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

def test_find_duplicate_is_case_insensitive(session):
    repo.create_perfume(session, PerfumeCreate(name="Aventus", house="Creed", notes=[]))
    assert repo.find_duplicate(session, "aventus", "CREED") is not None

def test_notes_missing_description(session):
    repo.create_perfume(session, _sample())  # creates bergamot, ambroxan (blank desc)
    missing = repo.notes_missing_description(session)
    assert {n.name for n in missing} == {"bergamot", "ambroxan"}

def test_apply_note_descriptions_sets_and_counts(session):
    repo.create_perfume(session, _sample())
    # Names matched case-insensitively; unknown names ignored; blanks skipped.
    updated = repo.apply_note_descriptions(session, {
        "Bergamot": "Bright citrus.", "ambroxan": "Warm ambery musk.",
        "unknownnote": "ignored", "": "  "})
    assert updated == 2
    remaining = {n.name for n in repo.notes_missing_description(session)}
    assert remaining == set()  # both now described
