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

def test_list_perfumes_filters_by_status(session):
    repo.create_perfume(session, PerfumeCreate(name="Owned", house="H", notes=[]))  # default collection
    repo.create_perfume(session, PerfumeCreate(name="Wanted", house="H", status="saved", notes=[]))
    assert [p.name for p in repo.list_perfumes(session, status="collection")] == ["Owned"]
    assert [p.name for p in repo.list_perfumes(session, status="saved")] == ["Wanted"]
    assert {p.name for p in repo.list_perfumes(session)} == {"Owned", "Wanted"}  # no filter -> all

def test_update_moves_between_sections(session):
    created = repo.create_perfume(session, PerfumeCreate(name="Wanted", house="H", status="saved", notes=[]))
    from app.schemas import PerfumeUpdate
    moved = repo.update_perfume(session, created.id, PerfumeUpdate(status="collection"))
    assert moved.status == "collection"
    assert [p.name for p in repo.list_perfumes(session, status="saved")] == []

def test_notes_missing_enrichment_by_version(session):
    repo.create_perfume(session, _sample())  # bergamot, ambroxan at version 0 (stale)
    assert {n.name for n in repo.notes_missing_enrichment(session)} == {"bergamot", "ambroxan"}
    # Enriching stamps the current version, so they drop out of "missing".
    repo.apply_note_enrichment(session, {
        "bergamot": {"origin": "natural"}, "ambroxan": {"origin": "synthetic"}})
    assert repo.notes_missing_enrichment(session) == []

def test_apply_note_enrichment_sets_new_fields_and_counts(session):
    repo.create_perfume(session, _sample())
    updated = repo.apply_note_enrichment(session, {
        "Bergamot": {"description": "Bright citrus.", "origin": "natural",
                     "production": "Cold-pressed.", "sourcing": "Calabria", "compounds": ""},
        "ambroxan": {"description": "Ambery.", "origin": "synthetic", "production": "From sclareol.",
                     "compounds": "ambrox", "proprietary_to": ""}})
    assert updated == 2
    notes = {n.name: n for n in repo.list_notes(session)}
    assert notes["bergamot"].sourcing == "Calabria"
    assert notes["ambroxan"].compounds == "ambrox"

def test_apply_note_enrichment_preserves_existing_description(session):
    repo.create_perfume(session, _sample())
    repo.apply_note_enrichment(session, {"bergamot": {
        "description": "ORIGINAL desc.", "origin": "natural", "production": "p1"}})
    # Re-enrich with a different description; the existing one must be kept.
    repo.apply_note_enrichment(session, {"bergamot": {
        "description": "NEW desc.", "origin": "both", "production": "p2",
        "proprietary_to": "Givaudan"}})
    note = {n.name: n for n in repo.list_notes(session)}["bergamot"]
    assert note.description == "ORIGINAL desc."  # preserved
    assert note.origin == "both" and note.proprietary_to == "Givaudan"  # refreshed
