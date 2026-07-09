from itertools import combinations
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models import Perfume, Note, PerfumeNote
from app.repository import _to_out, _normalize
from app.schemas import PerfumeOut

def search_perfumes(session: Session, q: str | None = None, family: str | None = None,
                    fmt: str | None = None) -> list[PerfumeOut]:
    stmt = select(Perfume)
    if q:
        term = _normalize(q)
        matching_ids = select(PerfumeNote.perfume_id).join(Note).where(
            Note.name.like(f"%{term}%"))
        stmt = stmt.where(
            (func.lower(Perfume.name).like(f"%{term}%")) |
            (Perfume.id.in_(matching_ids)))
    if family:
        stmt = stmt.where(Perfume.scent_family == family)
    if fmt:
        stmt = stmt.where(Perfume.formats.like(f"%{fmt}%"))
    stmt = stmt.order_by(Perfume.name)
    ps = session.execute(stmt).scalars().unique().all()
    return [_to_out(p) for p in ps]

def note_frequency(session: Session) -> list[tuple[str, int]]:
    stmt = (select(Note.name, func.count(func.distinct(PerfumeNote.perfume_id)))
            .join(PerfumeNote).group_by(Note.name)
            .order_by(func.count(func.distinct(PerfumeNote.perfume_id)).desc()))
    return [(name, count) for name, count in session.execute(stmt).all()]

def family_breakdown(session: Session) -> list[tuple[str, int]]:
    stmt = (select(Perfume.scent_family, func.count())
            .where(Perfume.scent_family.is_not(None))
            .group_by(Perfume.scent_family))
    return [(fam, count) for fam, count in session.execute(stmt).all()]

def format_breakdown(session: Session) -> dict[str, int]:
    result = {"full": 0, "travel": 0, "sample": 0}
    for (formats,) in session.execute(select(Perfume.formats)).all():
        for f in formats.split(","):
            if f in result:
                result[f] += 1
    return result

def _notes_of(p: Perfume) -> set[str]:
    return {pn.note.name for pn in p.perfume_notes}

def similar_pairs(session: Session) -> list[dict]:
    perfumes = session.execute(select(Perfume)).scalars().unique().all()
    pairs = []
    for a, b in combinations(perfumes, 2):
        shared = sorted(_notes_of(a) & _notes_of(b))
        if shared:
            pairs.append({"a": a.name, "b": b.name, "shared": shared,
                          "count": len(shared)})
    pairs.sort(key=lambda x: x["count"], reverse=True)
    return pairs
