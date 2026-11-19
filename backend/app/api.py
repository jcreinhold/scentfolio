"""Translate HTTP requests into collection reads, writes, and provider work."""

from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from app import agent, queries
from app import repository as repo
from app.agent import Draft
from app.ai_work import AIWork, Classify, Enrich, Lookup, SessionFactory
from app.deps import get_session_factory
from app.exports import perfume_csv
from app.llm import LookupError
from app.schemas import (
    Family,
    Format,
    GlossaryNote,
    NoteContent,
    NoteDetail,
    PerfumeCreate,
    PerfumeName,
    PerfumeOut,
    PerfumeReference,
    PerfumeSort,
    PerfumeUpdate,
    SortDirection,
    Status,
)

router = APIRouter(prefix="/api")
FactoryDep = Annotated[SessionFactory, Depends(get_session_factory)]
MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 40


class LookupRequest(BaseModel):
    """The fragrance name to research for an unsaved draft."""

    name: PerfumeName


class PerfumeQuery(BaseModel):
    """Optional filters, ordering, and page limits for a fragrance list."""

    q: str | None = Field(default=None, max_length=200)
    family: Family | None = None
    fmt: Format | None = None
    status: Status | None = None
    limit: int | None = Field(default=None, ge=1, le=MAX_PAGE_SIZE)
    offset: int = Field(default=0, ge=0)
    sort: PerfumeSort | None = None
    direction: SortDirection = "asc"


async def get_lookup() -> Lookup:
    """Provide the fragrance lookup callback through FastAPI's override hook."""
    return agent.lookup


async def get_note_enricher() -> Enrich:
    """Provide the batch callback for generating glossary entries."""
    return agent.enrich_notes


async def get_family_classifier() -> Classify:
    """Provide the callback for classifying a fragrance's scent families."""
    return agent.classify_families


async def get_ai_work(request: Request) -> AIWork:
    """Return the provider work service shared by this app's requests."""
    return request.app.state.ai_work


WorkDep = Annotated[AIWork, Depends(get_ai_work)]


@router.get("/health")
async def health() -> dict[str, str]:
    """Confirm that the HTTP server is responding."""
    return {"status": "ok"}


@router.post("/lookup")
async def lookup_perfume(
    req: LookupRequest, work: WorkDep, lookup: Annotated[Lookup, Depends(get_lookup)]
) -> Draft:
    """Research a fragrance and return a draft for review before saving.

    If all provider slots are busy, the server returns 503 with Retry-After.
    """
    try:
        return await work.lookup(req.name, lookup)
    except LookupError as exc:
        raise HTTPException(
            HTTPStatus.UNPROCESSABLE_ENTITY, f"Lookup failed: {exc}"
        ) from exc


@router.post("/perfumes", status_code=HTTPStatus.CREATED)
def create_perfume(data: PerfumeCreate, sessions: FactoryDep) -> PerfumeOut:
    """Save a fragrance and return the stored record, including its ID."""
    with sessions() as session:
        return repo.create_perfume(session, data)


@router.post("/perfumes/reclassify")
async def reclassify_perfumes(
    sessions: FactoryDep,
    work: WorkDep,
    classify: Annotated[Classify, Depends(get_family_classifier)],
) -> dict[str, int]:
    """Refresh stored scent families and report updates and provider failures.

    A result is applied only if the stored families still match the values
    read before classification.
    """
    try:
        return await work.reclassify(sessions, classify)
    except LookupError as exc:
        raise HTTPException(HTTPStatus.BAD_GATEWAY, str(exc)) from exc


@router.get("/perfumes/check-duplicate")
def check_duplicate(name: str, sessions: FactoryDep, house: str = ""):
    """Check whether a fragrance with this name and house already exists.

    Matching ignores case and trims input whitespace. The ID is null when
    no match is found.
    """
    with sessions() as session:
        duplicate = repo.find_duplicate(session, name, house)
        return {
            "duplicate": duplicate is not None,
            "id": duplicate.id if duplicate else None,
        }


@router.get("/perfumes")
def list_perfumes(
    sessions: FactoryDep,
    response: Response,
    query: Annotated[PerfumeQuery, Query()],
) -> list[PerfumeOut]:
    """List fragrances that match the supplied filters.

    A limit, nonzero offset, or sort requests a page. The response then
    includes X-Total-Count for all matches before paging.
    """
    with sessions() as session:
        if query.limit is not None or query.offset or query.sort is not None:
            items, total = repo.page_perfumes(
                session,
                repo.PerfumeFilter(
                    q=query.q,
                    family=query.family,
                    fmt=query.fmt,
                    status=query.status,
                ),
                limit=query.limit or DEFAULT_PAGE_SIZE,
                offset=query.offset,
                order=(query.sort, query.direction) if query.sort else None,
            )
            response.headers["X-Total-Count"] = str(total)
            return items
        if query.q or query.family or query.fmt:
            return repo.search_perfumes(
                session,
                q=query.q,
                family=query.family,
                fmt=query.fmt,
                status=query.status,
            )
        return repo.list_perfumes(session, status=query.status)


@router.get("/perfumes/export.csv")
def export_perfumes_csv(sessions: FactoryDep, status: Status | None = None) -> Response:
    """Download the full fragrance list as CSV, optionally filtered by status."""
    filename = f"scentfolio-{status or 'all'}.csv"
    with sessions() as session:
        perfumes = repo.list_perfumes(session, status=status)
    return Response(
        perfume_csv(perfumes),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/perfumes/{perfume_id}")
def get_perfume(perfume_id: int, sessions: FactoryDep) -> PerfumeOut:
    """Return a fragrance by ID or respond with 404 if it is missing."""
    with sessions() as session:
        perfume = repo.get_perfume(session, perfume_id)
    if perfume is None:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Perfume not found")
    return perfume


@router.patch("/perfumes/{perfume_id}")
def update_perfume(
    perfume_id: int, data: PerfumeUpdate, sessions: FactoryDep
) -> PerfumeOut:
    """Apply changes to a fragrance and return its stored values."""
    with sessions() as session:
        perfume = repo.update_perfume(session, perfume_id, data)
    if perfume is None:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Perfume not found")
    return perfume


@router.delete("/perfumes/{perfume_id}", status_code=HTTPStatus.NO_CONTENT)
def delete_perfume(perfume_id: int, sessions: FactoryDep) -> None:
    """Remove a fragrance and its note links, keeping the glossary entries."""
    with sessions() as session:
        if not repo.delete_perfume(session, perfume_id):
            raise HTTPException(HTTPStatus.NOT_FOUND, "Perfume not found")


@router.get("/notes")
def list_notes(sessions: FactoryDep) -> list[GlossaryNote]:
    """List glossary entries by name and flag those due for enrichment."""
    with sessions() as session:
        return [
            GlossaryNote(
                **NoteContent.model_validate(note).model_dump(),
                id=note.id,
                needs_enrichment=(note.detail_version or 0) < repo.ENRICH_VERSION,
            )
            for note in repo.list_notes(session)
        ]


@router.post("/notes/enrich-missing")
async def enrich_missing_notes(
    sessions: FactoryDep,
    work: WorkDep,
    enrich: Annotated[Enrich, Depends(get_note_enricher)],
) -> dict[str, int]:
    """Fill in missing or outdated glossary details in batches.

    Successful writes are kept. The response counts updated and remaining
    notes and includes a failure count when the provider misses entries.
    """
    try:
        return await work.enrich_missing(sessions, enrich)
    except LookupError as exc:
        raise HTTPException(HTTPStatus.BAD_GATEWAY, str(exc)) from exc


@router.get("/notes/{note_name:path}")
def note_detail(note_name: str, sessions: FactoryDep) -> NoteDetail:
    """Return a glossary entry and the fragrances that use it, or respond with 404."""
    with sessions() as session:
        note = repo.get_note(session, note_name)
        if note is None:
            raise HTTPException(HTTPStatus.NOT_FOUND, "Note not found")
        return NoteDetail(
            **NoteContent.model_validate(note).model_dump(),
            perfumes=[
                PerfumeReference.model_validate(perfume)
                for perfume in repo.perfumes_with_note(session, note.name)
            ],
        )


@router.get("/insights/notes")
def insight_notes(sessions: FactoryDep):
    """Rank notes by the number of fragrances that use them at each tier."""
    with sessions() as session:
        frequencies = queries.note_frequency_by_tier(session)
    return {
        tier: [{"note": name, "count": count} for name, count in rows]
        for tier, rows in frequencies.items()
    }


@router.get("/insights/families")
def insight_families(sessions: FactoryDep):
    """Count fragrances by scent family, including each tag on a fragrance."""
    with sessions() as session:
        families = queries.family_breakdown(session)
    return [{"family": family, "count": count} for family, count in families]


@router.get("/insights/formats")
def insight_formats(sessions: FactoryDep):
    """Count full bottles, travel sizes, and samples across stored fragrances."""
    with sessions() as session:
        return queries.format_breakdown(session)


@router.get("/insights/similar")
def insight_similar(sessions: FactoryDep):
    """Return the highest-scoring fragrance pairs and their shared traits."""
    return queries.similar_pairs(sessions)
