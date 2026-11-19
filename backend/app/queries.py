"""Read and score fragrance data for the Insights reports."""

from collections.abc import Callable
from dataclasses import dataclass
from heapq import nlargest
from itertools import combinations
from operator import itemgetter

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Note, Perfume, PerfumeNote


def note_frequency_by_tier(session: Session) -> dict[str, list[tuple[str, int]]]:
    """Report note counts for each tier, with the most frequent notes first.

    Counting separately keeps common base notes from dominating the report.
    """
    stmt = (
        select(
            Note.name,
            PerfumeNote.tier,
            func.count(func.distinct(PerfumeNote.perfume_id)),
        )
        .join(PerfumeNote)
        .group_by(Note.name, PerfumeNote.tier)
    )
    by_tier: dict[str, list[tuple[str, int]]] = {"top": [], "heart": [], "base": []}
    for name, tier, count in session.execute(stmt).all():
        if tier in by_tier:
            by_tier[tier].append((name, count))
    for lst in by_tier.values():
        lst.sort(key=lambda nc: nc[1], reverse=True)
    return by_tier


def family_breakdown(session: Session) -> list[tuple[str, int]]:
    """Count each family tag separately and return the most frequent first."""
    counts: dict[str, int] = {}
    for (families,) in session.execute(select(Perfume.scent_family)).all():
        for fam in (families or "").split(","):
            if fam:
                counts[fam] = counts.get(fam, 0) + 1
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)


def format_breakdown(session: Session) -> dict[str, int]:
    """Count each supported format, including zero counts for unused formats."""
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


@dataclass
class _Profile:
    name: str
    families: set[str]
    notes: dict[str, set[str]]


def _similarity_profiles(session: Session) -> list[_Profile]:
    statement = (
        select(
            Perfume.id,
            Perfume.name,
            Perfume.scent_family,
            PerfumeNote.tier,
            Note.name.label("note_name"),
        )
        .outerjoin(PerfumeNote, PerfumeNote.perfume_id == Perfume.id)
        .outerjoin(Note, Note.id == PerfumeNote.note_id)
        .order_by(Perfume.id)
    )
    profiles = {}
    for row in session.execute(statement):
        profile = profiles.get(row.id)
        if profile is None:
            profile = _Profile(
                row.name,
                {family for family in (row.scent_family or "").split(",") if family},
                {tier: set() for tier in TIERS},
            )
            profiles[row.id] = profile
        if row.tier in profile.notes and row.note_name is not None:
            profile.notes[row.tier].add(row.note_name)
    return list(profiles.values())


def _jaccard(a: set[str], b: set[str]) -> float:
    shared = len(a & b)
    return shared / (len(a) + len(b) - shared) if shared else 0.0


def _scored_pairs(profiles: list[_Profile]):
    for left, right in combinations(profiles, 2):
        score = FAMILY_WEIGHT * _jaccard(left.families, right.families) + sum(
            weight * _jaccard(left.notes[tier], right.notes[tier])
            for tier, weight in TIER_WEIGHTS.items()
        )
        if score > 0:
            yield round(score, 3), left, right


def similar_pairs(sessions: Callable[[], Session], limit: int = 15) -> list[dict]:
    """Rank perfume pairs by a tier-aware, family-weighted similarity.

    Compare shared notes and families against the full sets using Jaccard
    similarity. Give base notes less weight because they are common.

    Return up to limit pairs with positive scores before rounding, highest
    first, and include their shared notes and families.
    """
    # Finish the DB read before the CPU work. Profiles carry only detached values.
    with sessions() as session:
        profiles = _similarity_profiles(session)
    # Retain only the winners and preserve the original rounding and tie order.
    best = nlargest(limit, _scored_pairs(profiles), key=itemgetter(0))
    return [
        {
            "a": left.name,
            "b": right.name,
            "score": score,
            "shared_families": sorted(left.families & right.families),
            "shared_top": sorted(left.notes["top"] & right.notes["top"]),
            "shared_heart": sorted(left.notes["heart"] & right.notes["heart"]),
            "shared_base": sorted(left.notes["base"] & right.notes["base"]),
        }
        for score, left, right in best
    ]
