from app.models import Perfume, Note, PerfumeNote


def test_perfume_note_relationship(session):
    note = Note(name="bergamot", family="Citrus")
    perfume = Perfume(
        name="Sauvage",
        house="Dior",
        year=2015,
        scent_family="Fresh",
        formats="full,sample",
    )
    session.add_all([note, perfume])
    session.flush()
    session.add(PerfumeNote(perfume_id=perfume.id, note_id=note.id, tier="top"))
    session.commit()

    reloaded = session.get(Perfume, perfume.id)
    assert reloaded.perfume_notes[0].note.name == "bergamot"
    assert reloaded.perfume_notes[0].tier == "top"
