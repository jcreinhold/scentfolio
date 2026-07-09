from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Perfume, Note, PerfumeNote
from app.schemas import PerfumeCreate, PerfumeOut, NoteOut, PerfumeUpdate

def _normalize(name: str) -> str:
    return name.strip().lower()

def _get_or_create_note(session: Session, name: str, family: str | None) -> Note:
    norm = _normalize(name)
    note = session.execute(select(Note).where(Note.name == norm)).scalar_one_or_none()
    if note is None:
        note = Note(name=norm, family=family)
        session.add(note)
        session.flush()
    elif note.family is None and family:
        note.family = family
    return note

def _to_out(p: Perfume) -> PerfumeOut:
    notes = [NoteOut(id=pn.note.id, name=pn.note.name, tier=pn.tier,
                     family=pn.note.family) for pn in p.perfume_notes]
    return PerfumeOut(
        id=p.id, name=p.name, house=p.house, perfumer=p.perfumer, year=p.year,
        scent_family=p.scent_family, description=p.description,
        my_impressions=p.my_impressions,
        formats=[f for f in p.formats.split(",") if f],
        source_urls=[u for u in p.source_urls.split("\n") if u],
        notes=notes)

def create_perfume(session: Session, data: PerfumeCreate) -> PerfumeOut:
    p = Perfume(name=data.name, house=data.house, perfumer=data.perfumer,
                year=data.year, scent_family=data.scent_family,
                description=data.description, my_impressions=data.my_impressions,
                formats=",".join(data.formats), source_urls="\n".join(data.source_urls))
    session.add(p)
    session.flush()
    for n in data.notes:
        note = _get_or_create_note(session, n.name, n.family)
        session.add(PerfumeNote(perfume_id=p.id, note_id=note.id, tier=n.tier))
    session.commit()
    session.refresh(p)
    return _to_out(p)

def get_perfume(session: Session, perfume_id: int) -> PerfumeOut | None:
    p = session.get(Perfume, perfume_id)
    return _to_out(p) if p else None

def list_perfumes(session: Session) -> list[PerfumeOut]:
    ps = session.execute(select(Perfume).order_by(Perfume.created_at.desc())).scalars().all()
    return [_to_out(p) for p in ps]

def update_perfume(session: Session, perfume_id: int, data: PerfumeUpdate) -> PerfumeOut | None:
    p = session.get(Perfume, perfume_id)
    if not p:
        return None
    if data.my_impressions is not None:
        p.my_impressions = data.my_impressions
    if data.formats is not None:
        p.formats = ",".join(data.formats)
    session.commit()
    session.refresh(p)
    return _to_out(p)

def delete_perfume(session: Session, perfume_id: int) -> bool:
    p = session.get(Perfume, perfume_id)
    if not p:
        return False
    session.delete(p)
    session.commit()
    return True

def list_notes(session: Session) -> list[Note]:
    return list(session.execute(select(Note).order_by(Note.name)).scalars().all())

def perfumes_with_note(session: Session, note_name: str) -> list[Perfume]:
    norm = _normalize(note_name)
    stmt = (select(Perfume).join(PerfumeNote).join(Note)
            .where(Note.name == norm).order_by(Perfume.name))
    return list(session.execute(stmt).scalars().unique().all())

def find_duplicate(session: Session, name: str, house: str) -> Perfume | None:
    stmt = select(Perfume).where(Perfume.name == name, Perfume.house == house)
    return session.execute(stmt).scalars().first()
