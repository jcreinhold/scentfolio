from app import queries
from app import repository as repo
from app.schemas import NoteInput, PerfumeCreate


def _seed(session):
    repo.create_perfume(
        session,
        PerfumeCreate(
            name="Sauvage",
            house="Dior",
            scent_families=["Fresh", "Woody"],
            formats=["full"],
            notes=[
                NoteInput(name="bergamot", tier="top"),
                NoteInput(name="ambroxan", tier="base"),
            ],
        ),
    )
    repo.create_perfume(
        session,
        PerfumeCreate(
            name="Aventus",
            house="Creed",
            scent_families=["Chypre", "Woody"],
            formats=["sample"],
            notes=[
                NoteInput(name="bergamot", tier="top"),
                NoteInput(name="birch", tier="heart"),
            ],
        ),
    )


def test_note_frequency_by_tier(session):
    _seed(session)
    by_tier = queries.note_frequency_by_tier(session)
    assert {tier: dict(counts) for tier, counts in by_tier.items()} == {
        "top": {"bergamot": 2},
        "heart": {"birch": 1},
        "base": {"ambroxan": 1},
    }


def test_family_breakdown(session):
    _seed(session)
    assert dict(queries.family_breakdown(session)) == {
        "Woody": 2,
        "Fresh": 1,
        "Chypre": 1,
    }


def test_similarity_is_tier_aware_and_family_weighted(session):
    _seed(session)
    pairs = queries.similar_pairs(session)
    top = pairs[0]
    # Sauvage & Aventus share bergamot in the TOP tier and the Woody family.
    assert {top["a"], top["b"]} == {"Sauvage", "Aventus"}
    assert top["shared_top"] == ["bergamot"]
    assert top["shared_families"] == ["Woody"]
    assert top["shared_heart"] == [] and top["shared_base"] == []
    assert 0 < top["score"] <= 1


def test_similarity_prefers_same_tier_same_family_over_diluted_base(session):
    # A: fresh citrus with a bergamot TOP note.
    repo.create_perfume(
        session,
        PerfumeCreate(
            name="A",
            house="H",
            scent_families=["Fresh"],
            notes=[NoteInput(name="bergamot", tier="top")],
        ),
    )
    # B: same family + shares bergamot in the SAME (top) tier -> should rank high.
    repo.create_perfume(
        session,
        PerfumeCreate(
            name="B",
            house="H",
            scent_families=["Fresh"],
            notes=[
                NoteInput(name="bergamot", tier="top"),
                NoteInput(name="lemon", tier="top"),
            ],
        ),
    )
    # C: note-heavy, different family; only overlaps A on a common BASE note (musk).
    repo.create_perfume(
        session,
        PerfumeCreate(
            name="C",
            house="H",
            scent_families=["Gourmand"],
            notes=[
                NoteInput(name=n, tier="base")
                for n in ("musk", "vanilla", "caramel", "tonka", "cocoa", "amber")
            ],
        ),
    )
    repo.create_perfume(
        session,
        PerfumeCreate(
            name="A2musk",
            house="H",
            scent_families=["Fresh"],
            notes=[NoteInput(name="musk", tier="base")],
        ),
    )  # gives C a base overlap partner

    pairs = queries.similar_pairs(session)
    top = pairs[0]
    # The genuine top/family match (A↔B) beats any pairing that leans on base overlap.
    assert {top["a"], top["b"]} == {"A", "B"}
    a_b = next(p for p in pairs if {p["a"], p["b"]} == {"A", "B"})
    c_pairs = [p for p in pairs if "C" in (p["a"], p["b"])]
    assert all(a_b["score"] > cp["score"] for cp in c_pairs)
