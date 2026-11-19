"""Read and write collection records within caller-owned database sessions."""

from dataclasses import dataclass

from sqlalchemy import case, false, func, literal, select, update
from sqlalchemy.orm import Session, load_only, selectinload

from app.models import Note, Perfume, PerfumeNote
from app.schemas import (
    NoteOut,
    PerfumeCreate,
    PerfumeOut,
    PerfumeSort,
    PerfumeUpdate,
    SortDirection,
)

ENRICH_VERSION = 3
_PERFUME_NOTES = (
    selectinload(Perfume.perfume_notes)
    .joinedload(PerfumeNote.note)
    .load_only(Note.id, Note.name, Note.family)
)


@dataclass(frozen=True, kw_only=True)
class PerfumeFilter:
    """The same match criteria for both full search results and paged lists."""

    q: str | None = None
    family: str | None = None
    fmt: str | None = None
    status: str | None = None


def normalize_note_name(name: str) -> str:
    """Trim and lowercase a note name to get its shared glossary key."""
    return name.strip().lower()


def _get_or_create_note(session: Session, name: str, family: str | None) -> Note:
    """Reuse a glossary entry and fill its family only when it has none."""
    norm = normalize_note_name(name)
    note = session.execute(select(Note).where(Note.name == norm)).scalar_one_or_none()
    if note is None:
        note = Note(name=norm, family=family)
        session.add(note)
        session.flush()
    elif note.family is None and family:
        note.family = family
    return note


def _to_out(p: Perfume) -> PerfumeOut:
    notes = [
        NoteOut(id=pn.note.id, name=pn.note.name, tier=pn.tier, family=pn.note.family)
        for pn in p.perfume_notes
    ]
    return PerfumeOut(
        id=p.id,
        name=p.name,
        status=p.status,
        house=p.house,
        perfumer=p.perfumer,
        year=p.year,
        scent_families=[f for f in (p.scent_family or "").split(",") if f],
        description=p.description,
        my_impressions=p.my_impressions,
        formats=[f for f in p.formats.split(",") if f],
        source_urls=[u for u in p.source_urls.split("\n") if u],
        notes=notes,
    )


def create_perfume(session: Session, data: PerfumeCreate) -> PerfumeOut:
    """Commit a new perfume, reusing glossary notes and deduplicating tier links."""
    p = Perfume(
        name=data.name,
        status=data.status,
        house=data.house,
        perfumer=data.perfumer,
        year=data.year,
        scent_family=",".join(data.scent_families),
        description=data.description,
        my_impressions=data.my_impressions,
        formats=",".join(data.formats),
        source_urls="\n".join(data.source_urls),
    )
    session.add(p)
    session.flush()
    associations = set()
    for n in data.notes:
        note = _get_or_create_note(session, n.name, n.family)
        key = (note.id, n.tier)
        if key in associations:
            continue
        associations.add(key)
        session.add(PerfumeNote(perfume_id=p.id, note_id=note.id, tier=n.tier))
    session.commit()
    session.refresh(p)
    return _to_out(p)


def get_perfume(session: Session, perfume_id: int) -> PerfumeOut | None:
    """Read a perfume and its notes as plain data, or return None if absent."""
    p = session.get(Perfume, perfume_id, options=[_PERFUME_NOTES])
    return _to_out(p) if p else None


def list_perfumes(session: Session, status: str | None = None) -> list[PerfumeOut]:
    """List perfumes newest first, across both statuses unless one is supplied."""
    stmt = select(Perfume).options(_PERFUME_NOTES).order_by(Perfume.created_at.desc())
    if status:
        stmt = stmt.where(Perfume.status == status)
    ps = session.execute(stmt).scalars().all()
    return [_to_out(p) for p in ps]


def _perfume_filters(filters: PerfumeFilter):
    conditions = []
    if filters.status:
        conditions.append(Perfume.status == filters.status)
    if filters.q:
        term = filters.q.strip().lower()
        matching_ids = (
            select(PerfumeNote.perfume_id)
            .join(Note)
            .where(Note.name.contains(term, autoescape=True))
        )
        conditions.append(
            func.lower(Perfume.name).contains(term, autoescape=True)
            | (Perfume.id.in_(matching_ids))
        )
    for value, column in (
        (filters.family, Perfume.scent_family),
        (filters.fmt, Perfume.formats),
    ):
        if value:
            if "," in value:
                return [false()]
            members = literal(",") + func.coalesce(column, "") + literal(",")
            conditions.append(members.contains(f",{value},", autoescape=True))
    return conditions


def search_perfumes(
    session: Session,
    q: str | None = None,
    family: str | None = None,
    fmt: str | None = None,
    status: str | None = None,
) -> list[PerfumeOut]:
    """List all matches in name order, searching perfume and note names."""
    filters = PerfumeFilter(q=q, family=family, fmt=fmt, status=status)
    stmt = (
        select(Perfume)
        .options(_PERFUME_NOTES)
        .where(*_perfume_filters(filters))
        .order_by(Perfume.name)
    )
    ps = session.scalars(stmt).all()
    return [_to_out(p) for p in ps]


def _page_order(order: tuple[PerfumeSort, SortDirection] | None):
    """Keep page order stable with a final ID tie-breaker and sort nulls last."""
    if order is None:
        return Perfume.created_at.desc(), Perfume.id.desc()

    sort, direction = order
    ties = [Perfume.id]
    if sort == "perfumer":
        perfumer = func.lower(func.nullif(Perfume.perfumer, ""))
        value = case((perfumer.is_not(None), func.count().over(partition_by=perfumer)))
        ties.insert(0, perfumer.asc())
    elif sort == "notes":
        value = (
            select(func.count())
            .where(PerfumeNote.perfume_id == Perfume.id)
            .correlate(Perfume)
            .scalar_subquery()
        )
    else:
        column = {
            "name": Perfume.name,
            "house": Perfume.house,
            "year": Perfume.year,
            "family": Perfume.scent_family,
        }[sort]
        value = column if sort == "year" else func.lower(func.nullif(column, ""))
    sortable = value.desc() if direction == "desc" else value.asc()
    return sortable.nulls_last(), *ties


def page_perfumes(
    session: Session,
    filters: PerfumeFilter,
    *,
    limit: int,
    offset: int = 0,
    order: tuple[PerfumeSort, SortDirection] | None = None,
) -> tuple[list[PerfumeOut], int]:
    """Return a page and the total match count, even when the page is empty.

    Apply filters and ordering before slicing. Default to newest first.
    """
    conditions = _perfume_filters(filters)
    page = (
        select(Perfume, func.count().over().label("total"))
        .where(*conditions)
        .order_by(*_page_order(order))
        .limit(limit)
        .offset(offset)
        .options(_PERFUME_NOTES)
    )
    rows = session.execute(page).all()
    if rows:
        return [_to_out(perfume) for perfume, _ in rows], rows[0].total
    total = session.scalar(select(func.count()).select_from(Perfume).where(*conditions))
    return [], total


def update_perfume(
    session: Session, perfume_id: int, data: PerfumeUpdate
) -> PerfumeOut | None:
    """Commit changes to the supplied fields and return the resulting perfume.

    Return None for a missing ID. If all fields are null, just read the record.
    """
    changes = {}
    if data.my_impressions is not None:
        changes["my_impressions"] = data.my_impressions
    if data.formats is not None:
        changes["formats"] = ",".join(data.formats)
    if data.scent_families is not None:
        changes["scent_family"] = ",".join(data.scent_families)
    if data.status is not None:
        changes["status"] = data.status
    if not changes:
        return get_perfume(session, perfume_id)

    matches_id = Perfume.id == perfume_id
    updated = session.execute(update(Perfume).where(matches_id).values(changes))
    if updated.rowcount == 0:
        session.commit()
        return None

    perfume = session.scalar(
        select(Perfume)
        .where(matches_id)
        .options(_PERFUME_NOTES)
        .execution_options(populate_existing=True)
    )
    # Build the response while the row still belongs to this write transaction.
    result = _to_out(perfume)
    session.commit()
    return result


def set_scent_families(
    session: Session,
    perfume_id: int,
    families: list[str],
    *,
    expected_families: list[str] | None = None,
) -> bool:
    """Update a perfume's scent families and commit the transaction.

    If expected_families is supplied, update only when the stored list
    still matches it. Return True if a row matched the update.
    """
    statement = update(Perfume).where(Perfume.id == perfume_id)
    if expected_families is not None:
        statement = statement.where(
            func.coalesce(Perfume.scent_family, "") == ",".join(expected_families)
        )
    result = session.execute(statement.values(scent_family=",".join(families)))
    session.commit()
    return result.rowcount > 0


def delete_perfume(session: Session, perfume_id: int) -> bool:
    """Commit removal of a perfume and its links, or return False if absent."""
    p = session.get(Perfume, perfume_id)
    if not p:
        return False
    session.delete(p)
    session.commit()
    return True


def list_notes(session: Session) -> list[Note]:
    """Return all glossary rows sorted by name, including unused notes."""
    return list(session.execute(select(Note).order_by(Note.name)).scalars().all())


def get_note(session: Session, name: str) -> Note | None:
    """Look up a note by its normalized name, returning None if absent."""
    return session.scalar(select(Note).where(Note.name == normalize_note_name(name)))


_STALE_ENRICHMENT = func.coalesce(Note.detail_version, 0) < ENRICH_VERSION


def notes_missing_enrichment(session: Session) -> list[Note]:
    """List notes with missing or outdated enrichment in name order."""
    stmt = select(Note).where(_STALE_ENRICHMENT).order_by(Note.name)
    return list(session.execute(stmt).scalars().all())


def apply_note_enrichment(session: Session, mapping: dict[str, dict]) -> int:
    """Commit enrichment for notes still stale, preserving existing descriptions.

    Return the number of notes updated.
    """
    updated = 0
    for name, data in mapping.items():
        result = session.execute(
            update(Note)
            .where(Note.name == normalize_note_name(name), _STALE_ENRICHMENT)
            .values(
                origin=data.get("origin", ""),
                production=data.get("production", ""),
                compounds=data.get("compounds", ""),
                sourcing=data.get("sourcing", ""),
                proprietary_to=data.get("proprietary_to", ""),
                history=data.get("history", ""),
                description=func.coalesce(
                    func.nullif(Note.description, ""), data.get("description") or ""
                ),
                detail_version=ENRICH_VERSION,
            )
        )
        updated += result.rowcount
    session.commit()
    return updated


def perfumes_with_note(session: Session, note_name: str) -> list[Perfume]:
    """List each perfume using the note once, in perfume name order."""
    norm = normalize_note_name(note_name)
    stmt = (
        select(Perfume)
        .options(load_only(Perfume.id, Perfume.name, Perfume.house))
        .join(PerfumeNote)
        .join(Note)
        .where(Note.name == norm)
        .order_by(Perfume.name)
    )
    return list(session.execute(stmt).scalars().unique().all())


def find_duplicate(session: Session, name: str, house: str) -> Perfume | None:
    """Find a name-and-house match after trimming and lowercasing the inputs."""
    stmt = select(Perfume).where(
        func.lower(Perfume.name) == name.strip().lower(),
        func.lower(Perfume.house) == house.strip().lower(),
    )
    return session.execute(stmt).scalars().first()
