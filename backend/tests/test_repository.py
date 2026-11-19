from sqlalchemy import event

from app import repository as repo
from app.deps import open_database
from app.schemas import NoteInput, PerfumeCreate, PerfumeUpdate


def _sample(name="Sauvage", house="Dior"):
    return PerfumeCreate(
        name=name,
        house=house,
        scent_families=["Fresh"],
        formats=["full"],
        notes=[
            NoteInput(name="Bergamot", tier="top", family="Citrus"),
            NoteInput(name="ambroxan", tier="base"),
        ],
    )


def test_scent_families_round_trip_multi(session):
    created = repo.create_perfume(
        session,
        PerfumeCreate(
            name="Milk", house="Snif", scent_families=["Gourmand", "Woody"], notes=[]
        ),
    )
    assert repo.get_perfume(session, created.id).scent_families == ["Gourmand", "Woody"]


def test_set_scent_families_overwrites(session):
    created = repo.create_perfume(session, _sample())  # ["Fresh"]
    assert repo.set_scent_families(session, created.id, ["Gourmand", "Green"]) is True
    assert repo.get_perfume(session, created.id).scent_families == ["Gourmand", "Green"]


def test_stale_classifier_does_not_overwrite_a_manual_edit(session):
    created = repo.create_perfume(session, _sample())
    repo.update_perfume(session, created.id, PerfumeUpdate(scent_families=["Woody"]))
    assert not repo.set_scent_families(
        session, created.id, ["Green"], expected_families=created.scent_families
    )
    assert repo.get_perfume(session, created.id).scent_families == ["Woody"]
    assert repo.set_scent_families(
        session, created.id, ["Green"], expected_families=["Woody"]
    )
    assert repo.get_perfume(session, created.id).scent_families == ["Green"]


def test_create_normalizes_and_dedupes_notes(session):
    repo.create_perfume(session, _sample())
    repo.create_perfume(session, _sample(name="Homme", house="Dior"))
    # "Bergamot" and "bergamot" should be ONE note row (normalized lowercase)
    all_notes = repo.list_notes(session)
    names = [n.name for n in all_notes]
    assert names.count("bergamot") == 1


def test_same_normalized_note_and_tier_collapses_but_other_tiers_survive(session):
    perfume = repo.create_perfume(
        session,
        PerfumeCreate(
            name="Layered Citrus",
            notes=[
                NoteInput(name="Bergamot", tier="top"),
                NoteInput(name=" BERGAMOT ", tier="top", family="Citrus"),
                NoteInput(name="bergamot", tier="base"),
            ],
        ),
    )
    note = repo.get_note(session, " BERGAMOT ")
    assert note is not None and note.family == "Citrus"
    assert sorted((n.id, n.tier) for n in perfume.notes) == [
        (note.id, "base"),
        (note.id, "top"),
    ]


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
    repo.create_perfume(
        session, PerfumeCreate(name="Owned", house="H", notes=[])
    )  # default collection
    repo.create_perfume(
        session, PerfumeCreate(name="Wanted", house="H", status="saved", notes=[])
    )
    assert [p.name for p in repo.list_perfumes(session, status="collection")] == [
        "Owned"
    ]
    assert [p.name for p in repo.list_perfumes(session, status="saved")] == ["Wanted"]
    assert [p.name for p in repo.list_perfumes(session)] == ["Wanted", "Owned"]


def test_search_matches_name_or_note(session):
    repo.create_perfume(session, _sample(name="Aventus", house="Creed"))
    repo.create_perfume(session, _sample())

    by_name = repo.search_perfumes(session, q=" AVEN ")
    assert [p.name for p in by_name] == ["Aventus"]
    by_note = repo.search_perfumes(session, q="bergamot")
    assert [p.name for p in by_note] == ["Aventus", "Sauvage"]


def test_search_filters_by_family_format_and_status(session):
    repo.create_perfume(
        session,
        PerfumeCreate(
            name="Sauvage", scent_families=["Fresh", "Woody"], formats=["full"]
        ),
    )
    repo.create_perfume(
        session,
        PerfumeCreate(
            name="Aventus",
            scent_families=["Chypre", "Woody"],
            formats=["sample"],
            status="saved",
        ),
    )

    chypre = repo.search_perfumes(session, family="Chypre")
    assert [p.name for p in chypre] == ["Aventus"]
    woody = repo.search_perfumes(session, family="Woody")
    assert [p.name for p in woody] == ["Aventus", "Sauvage"]
    full = repo.search_perfumes(session, fmt="full")
    assert [p.name for p in full] == ["Sauvage"]
    saved_woody = repo.search_perfumes(session, family="Woody", status="saved")
    assert [p.name for p in saved_woody] == ["Aventus"]
    assert repo.search_perfumes(session, family="Wood") == []
    assert repo.search_perfumes(session, family="Fresh,Woody") == []
    assert repo.search_perfumes(session, fmt="ull") == []


def test_search_treats_sql_wildcards_as_literal_characters(session):
    repo.create_perfume(session, PerfumeCreate(name="100% Rose"))
    repo.create_perfume(
        session,
        PerfumeCreate(name="100X Rose", notes=[NoteInput(name="a_b", tier="heart")]),
    )
    assert [p.name for p in repo.search_perfumes(session, q="100% ")] == ["100% Rose"]
    assert [p.name for p in repo.search_perfumes(session, q="a_b")] == ["100X Rose"]


def test_page_sorts_filtered_records_before_slicing_with_stable_ties(session):
    for perfume in (
        PerfumeCreate(
            name="Aster",
            house="Z House",
            perfumer="Marie",
            year=2001,
            scent_families=["Woody"],
            notes=_sample().notes,
        ),
        PerfumeCreate(name="Billow", perfumer="Zita", status="saved"),
        PerfumeCreate(
            name="Cedar",
            house="A House",
            perfumer="MARIE",
            notes=[NoteInput(name="cedar", tier="base")],
        ),
        PerfumeCreate(
            name="Dawn", perfumer="Zita", year=1994, scent_families=["Floral"]
        ),
        PerfumeCreate(name="Evening", house="B House", scent_families=["Citrus"]),
        PerfumeCreate(
            name="Ferns", house="B House", perfumer="Ari", scent_families=["Citrus"]
        ),
    ):
        repo.create_perfume(session, perfume)

    filters = repo.PerfumeFilter(status="collection")
    for sort, direction, expected in (
        (None, "asc", ["Ferns", "Evening", "Dawn", "Cedar", "Aster"]),
        ("name", "desc", ["Ferns", "Evening", "Dawn", "Cedar", "Aster"]),
        ("house", "desc", ["Aster", "Evening", "Ferns", "Cedar", "Dawn"]),
        ("year", "asc", ["Dawn", "Aster", "Cedar", "Evening", "Ferns"]),
        ("family", "asc", ["Evening", "Ferns", "Dawn", "Aster", "Cedar"]),
        ("notes", "desc", ["Aster", "Cedar", "Dawn", "Evening", "Ferns"]),
        ("perfumer", "asc", ["Ferns", "Dawn", "Aster", "Cedar", "Evening"]),
        ("perfumer", "desc", ["Aster", "Cedar", "Ferns", "Dawn", "Evening"]),
    ):
        rows, total = repo.page_perfumes(
            session,
            filters,
            limit=2,
            offset=1,
            order=(sort, direction) if sort is not None else None,
        )
        assert [row.name for row in rows] == expected[1:3], (sort, direction)
        assert total == len(expected)
    assert repo.page_perfumes(session, filters, limit=2, offset=20) == (
        [],
        5,
    )


def test_update_moves_between_sections(session):
    created = repo.create_perfume(
        session, PerfumeCreate(name="Wanted", house="H", status="saved", notes=[])
    )

    moved = repo.update_perfume(session, created.id, PerfumeUpdate(status="collection"))
    assert moved.status == "collection"
    assert [p.name for p in repo.list_perfumes(session, status="saved")] == []


def test_update_returns_snapshot_when_record_disappears_after_commit(tmp_path):
    engine, sessions = open_database(f"sqlite:///{tmp_path / 'collection.db'}")
    try:
        with sessions() as session:
            perfume_id = repo.create_perfume(session, _sample()).id

        def delete_after_commit(_):
            with sessions() as other:
                assert repo.delete_perfume(other, perfume_id)

        with sessions() as session:
            event.listen(session, "after_commit", delete_after_commit, once=True)
            updated = repo.update_perfume(
                session, perfume_id, PerfumeUpdate(my_impressions="Updated")
            )

        assert updated is not None and updated.my_impressions == "Updated"
        with sessions() as session:
            assert repo.update_perfume(session, perfume_id, PerfumeUpdate()) is None
    finally:
        engine.dispose()


def test_notes_missing_enrichment_by_version(session):
    repo.create_perfume(session, _sample())  # bergamot, ambroxan at version 0 (stale)
    assert {n.name for n in repo.notes_missing_enrichment(session)} == {
        "bergamot",
        "ambroxan",
    }
    # Enriching stamps the current version, so they drop out of "missing".
    repo.apply_note_enrichment(
        session,
        {"bergamot": {"origin": "natural"}, "ambroxan": {"origin": "synthetic"}},
    )
    assert repo.notes_missing_enrichment(session) == []


def test_apply_note_enrichment_sets_new_fields_and_counts(session):
    repo.create_perfume(session, _sample())
    enrichment = {
        "Bergamot": {
            "description": "Bright citrus.",
            "origin": "natural",
            "production": "Cold-pressed.",
            "sourcing": "Calabria",
            "compounds": "",
        },
        "ambroxan": {
            "description": "Ambery.",
            "origin": "synthetic",
            "production": "From sclareol.",
            "compounds": "ambrox",
            "proprietary_to": "",
        },
    }
    updated = repo.apply_note_enrichment(session, enrichment)
    assert updated == len(enrichment)
    notes = {n.name: n for n in repo.list_notes(session)}
    assert notes["bergamot"].sourcing == "Calabria"
    assert notes["ambroxan"].compounds == "ambrox"


def test_apply_note_enrichment_preserves_existing_description(session):
    repo.create_perfume(session, _sample())
    note = repo.get_note(session, "bergamot")
    note.description = "Original description"
    session.commit()
    assert (
        repo.apply_note_enrichment(
            session,
            {
                "bergamot": {
                    "description": "Replacement description",
                    "origin": "both",
                    "proprietary_to": "Givaudan",
                }
            },
        )
        == 1
    )
    assert repo.apply_note_enrichment(session, {"bergamot": {"origin": "natural"}}) == 0
    session.refresh(note)
    assert note.description == "Original description"
    assert note.origin == "both" and note.proprietary_to == "Givaudan"
