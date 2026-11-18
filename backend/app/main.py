import csv
import io
from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.deps import get_session
from app import repository as repo, queries
from app.schemas import PerfumeCreate, PerfumeUpdate
from concurrent.futures import ThreadPoolExecutor
from app.agent import (
    lookup as live_lookup,
    enrich_notes as live_enrich,
    classify_families as live_classify,
    LookupError,
)


class LookupRequest(BaseModel):
    name: str


def get_lookup():
    return live_lookup


def get_note_enricher():
    return live_enrich


def get_family_classifier():
    return live_classify


ENRICH_CHUNK = 12  # smaller batches: v3 enrichment returns long-form content
RECLASSIFY_WORKERS = 4

app = FastAPI(title="Scentfolio")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/lookup")
def lookup_perfume(req: LookupRequest, lookup=Depends(get_lookup)):
    try:
        draft = lookup(req.name)
    except LookupError as e:
        raise HTTPException(422, f"Lookup failed: {e}")
    return draft.model_dump()


@app.post("/api/perfumes", status_code=201)
def create_perfume(data: PerfumeCreate, session: Session = Depends(get_session)):
    return repo.create_perfume(session, data)


@app.post("/api/perfumes/reclassify")
def reclassify_perfumes(
    session: Session = Depends(get_session), classify=Depends(get_family_classifier)
):
    perfumes = repo.list_perfumes(session)

    def work(p):
        try:
            return p.id, classify(p.name, p.house, [n.name for n in p.notes])
        except LookupError:
            return p.id, None

    # Classify concurrently (network-bound, no DB); apply updates single-threaded.
    with ThreadPoolExecutor(max_workers=RECLASSIFY_WORKERS) as ex:
        results = list(ex.map(work, perfumes))
    updated = 0
    for pid, families in results:
        if families and repo.set_scent_families(session, pid, families):
            updated += 1
    return {"updated": updated}


@app.get("/api/perfumes/check-duplicate")
def check_duplicate(
    name: str, house: str = "", session: Session = Depends(get_session)
):
    dup = repo.find_duplicate(session, name, house)
    return {"duplicate": dup is not None, "id": dup.id if dup else None}


@app.get("/api/perfumes")
def list_perfumes(
    q: str | None = None,
    family: str | None = None,
    fmt: str | None = None,
    status: str | None = None,
    session: Session = Depends(get_session),
):
    if q or family or fmt:
        return repo.search_perfumes(session, q=q, family=family, fmt=fmt, status=status)
    return repo.list_perfumes(session, status=status)


CSV_COLUMNS = [
    "name",
    "status",
    "house",
    "perfumer",
    "year",
    "families",
    "formats",
    "top_notes",
    "heart_notes",
    "base_notes",
    "description",
    "impressions",
]


@app.get("/api/perfumes/export.csv")
def export_perfumes_csv(
    status: str | None = None, session: Session = Depends(get_session)
):
    perfumes = repo.list_perfumes(session, status=status)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(CSV_COLUMNS)
    for p in perfumes:
        by_tier = {"top": [], "heart": [], "base": []}
        for n in p.notes:
            if n.tier in by_tier:
                by_tier[n.tier].append(n.name)
        writer.writerow(
            [
                p.name,
                p.status,
                p.house,
                p.perfumer or "",
                p.year or "",
                "; ".join(p.scent_families),
                "; ".join(p.formats),
                "; ".join(by_tier["top"]),
                "; ".join(by_tier["heart"]),
                "; ".join(by_tier["base"]),
                p.description,
                p.my_impressions,
            ]
        )
    filename = f"scentfolio-{status or 'all'}.csv"
    return Response(
        buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/perfumes/{perfume_id}")
def get_perfume(perfume_id: int, session: Session = Depends(get_session)):
    p = repo.get_perfume(session, perfume_id)
    if not p:
        raise HTTPException(404, "Perfume not found")
    return p


@app.patch("/api/perfumes/{perfume_id}")
def update_perfume(
    perfume_id: int, data: PerfumeUpdate, session: Session = Depends(get_session)
):
    p = repo.update_perfume(session, perfume_id, data)
    if not p:
        raise HTTPException(404, "Perfume not found")
    return p


@app.delete("/api/perfumes/{perfume_id}", status_code=204)
def delete_perfume(perfume_id: int, session: Session = Depends(get_session)):
    if not repo.delete_perfume(session, perfume_id):
        raise HTTPException(404, "Perfume not found")


@app.get("/api/notes")
def list_notes(session: Session = Depends(get_session)):
    return [
        {
            "id": n.id,
            "name": n.name,
            "family": n.family,
            "description": n.description,
            "origin": n.origin,
            "production": n.production,
            "compounds": n.compounds,
            "sourcing": n.sourcing,
            "proprietary_to": n.proprietary_to,
            "history": n.history,
        }
        for n in repo.list_notes(session)
    ]


@app.post("/api/notes/enrich-missing")
def enrich_missing_notes(
    session: Session = Depends(get_session), enrich=Depends(get_note_enricher)
):
    names = [n.name for n in repo.notes_missing_enrichment(session)]
    updated = 0
    # Persist per chunk so long runs make durable progress even if the request is
    # interrupted; a re-run resumes via the version check (notes_missing_enrichment).
    for i in range(0, len(names), ENRICH_CHUNK):
        chunk = names[i : i + ENRICH_CHUNK]
        try:
            updated += repo.apply_note_enrichment(session, enrich(chunk))
        except LookupError:
            continue  # skip a failed chunk; others still apply
    remaining = len(repo.notes_missing_enrichment(session))
    return {"updated": updated, "remaining": remaining}


@app.get("/api/notes/{note_name}")
def note_detail(note_name: str, session: Session = Depends(get_session)):
    notes = {n.name: n for n in repo.list_notes(session)}
    n = notes.get(note_name.strip().lower())
    perfumes = repo.perfumes_with_note(session, note_name)
    return {
        "name": note_name.strip().lower(),
        "family": n.family if n else None,
        "description": n.description if n else "",
        "origin": n.origin if n else "",
        "production": n.production if n else "",
        "compounds": n.compounds if n else "",
        "sourcing": n.sourcing if n else "",
        "proprietary_to": n.proprietary_to if n else "",
        "history": n.history if n else "",
        "perfumes": [{"id": p.id, "name": p.name, "house": p.house} for p in perfumes],
    }


@app.get("/api/insights/notes")
def insight_notes(session: Session = Depends(get_session)):
    by_tier = queries.note_frequency_by_tier(session)
    return {
        tier: [{"note": name, "count": c} for name, c in rows]
        for tier, rows in by_tier.items()
    }


@app.get("/api/insights/families")
def insight_families(session: Session = Depends(get_session)):
    return [{"family": f, "count": c} for f, c in queries.family_breakdown(session)]


@app.get("/api/insights/formats")
def insight_formats(session: Session = Depends(get_session)):
    return queries.format_breakdown(session)


@app.get("/api/insights/similar")
def insight_similar(session: Session = Depends(get_session)):
    return queries.similar_pairs(session)
