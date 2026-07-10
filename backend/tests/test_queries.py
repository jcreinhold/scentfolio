from app import repository as repo, queries
from app.schemas import PerfumeCreate, NoteInput

def _seed(session):
    repo.create_perfume(session, PerfumeCreate(
        name="Sauvage", house="Dior", scent_families=["Fresh", "Woody"], formats=["full"],
        notes=[NoteInput(name="bergamot", tier="top"), NoteInput(name="ambroxan", tier="base")]))
    repo.create_perfume(session, PerfumeCreate(
        name="Aventus", house="Creed", scent_families=["Chypre", "Woody"], formats=["sample"],
        notes=[NoteInput(name="bergamot", tier="top"), NoteInput(name="birch", tier="heart")]))

def test_search_matches_name_or_note(session):
    _seed(session)
    by_name = queries.search_perfumes(session, q="aven")
    assert [p.name for p in by_name] == ["Aventus"]
    by_note = queries.search_perfumes(session, q="bergamot")
    assert {p.name for p in by_note} == {"Sauvage", "Aventus"}

def test_filter_by_family_and_format(session):
    _seed(session)
    fam = queries.search_perfumes(session, family="Chypre")
    assert [p.name for p in fam] == ["Aventus"]
    # "Woody" is a secondary tag on BOTH -> any-match returns both.
    both = queries.search_perfumes(session, family="Woody")
    assert {p.name for p in both} == {"Sauvage", "Aventus"}
    fmt = queries.search_perfumes(session, fmt="full")
    assert [p.name for p in fmt] == ["Sauvage"]

def test_note_frequency(session):
    _seed(session)
    freq = dict(queries.note_frequency(session))
    assert freq["bergamot"] == 2
    assert freq["birch"] == 1

def test_family_breakdown(session):
    _seed(session)
    fams = dict(queries.family_breakdown(session))
    # Multi-tag rows contribute to each family: Woody appears on both.
    assert fams["Woody"] == 2
    assert fams["Fresh"] == 1 and fams["Chypre"] == 1

def test_similarity_shared_notes(session):
    _seed(session)
    pairs = queries.similar_pairs(session)
    # Sauvage & Aventus share bergamot -> one pair with shared count 1
    assert pairs[0]["shared"] == ["bergamot"]
