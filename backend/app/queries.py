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
        stmt = stmt.where(Perfume.scent_family.like(f"%{family}%"))
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
    """Count each family across perfumes. Families are stored comma-joined, so a
    perfume with multiple tags contributes to each. Sorted by count desc."""
    counts: dict[str, int] = {}
    for (families,) in session.execute(select(Perfume.scent_family)).all():
        for fam in (families or "").split(","):
            if fam:
                counts[fam] = counts.get(fam, 0) + 1
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)

def format_breakdown(session: Session) -> dict[str, int]:
    result = {"full": 0, "travel": 0, "sample": 0}
    for (formats,) in session.execute(select(Perfume.formats)).all():
        for f in formats.split(","):
            if f in result:
                result[f] += 1
    return result

TIERS = ("top", "heart", "base")
# Base notes are near-universal, so they carry the least weight; family overlap
# carries meaningful signal about overall impression.
TIER_WEIGHTS = {"top": 0.30, "heart": 0.30, "base": 0.15}
FAMILY_WEIGHT = 0.25

def _tiered_notes(p: Perfume) -> dict[str, set[str]]:
    tiers: dict[str, set[str]] = {t: set() for t in TIERS}
    for pn in p.perfume_notes:
        if pn.tier in tiers:
            tiers[pn.tier].add(pn.note.name)
    return tiers

def _families(p: Perfume) -> set[str]:
    return {f for f in (p.scent_family or "").split(",") if f}

def _jaccard(a: set[str], b: set[str]) -> float:
    union = a | b
    return len(a & b) / len(union) if union else 0.0

def similar_pairs(session: Session, limit: int = 15) -> list[dict]:
    """Rank perfume pairs by a tier-aware, family-weighted similarity.

    Uses per-tier and per-family Jaccard indices (normalized, so note-heavy
    perfumes don't dominate) combined into a 0-1 score. Base notes are
    down-weighted because they are common across most fragrances."""
    perfumes = session.execute(select(Perfume)).scalars().unique().all()
    prepared = [(p, _tiered_notes(p), _families(p)) for p in perfumes]
    pairs = []
    for (pa, ta, fa), (pb, tb, fb) in combinations(prepared, 2):
        family_j = _jaccard(fa, fb)
        score = FAMILY_WEIGHT * family_j + sum(
            TIER_WEIGHTS[t] * _jaccard(ta[t], tb[t]) for t in TIER_WEIGHTS)
        if score <= 0:
            continue
        pairs.append({
            "a": pa.name, "b": pb.name, "score": round(score, 3),
            "shared_families": sorted(fa & fb),
            "shared_top": sorted(ta["top"] & tb["top"]),
            "shared_heart": sorted(ta["heart"] & tb["heart"]),
            "shared_base": sorted(ta["base"] & tb["base"]),
        })
    pairs.sort(key=lambda x: x["score"], reverse=True)
    return pairs[:limit]
