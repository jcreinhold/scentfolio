from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.deps import get_session
from app import repository as repo, queries
from app.schemas import PerfumeCreate, PerfumeUpdate
from concurrent.futures import ThreadPoolExecutor
from app.agent import (lookup as live_lookup, enrich_notes as live_enrich,
                       classify_families as live_classify, LookupError)

class LookupRequest(BaseModel):
    name: str

def get_lookup():
    return live_lookup

def get_note_enricher():
    return live_enrich

def get_family_classifier():
    return live_classify

DESCRIBE_CHUNK = 25
RECLASSIFY_WORKERS = 4

app = FastAPI(title="Scentfolio")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
                   allow_methods=["*"], allow_headers=["*"])

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
def reclassify_perfumes(session: Session = Depends(get_session),
                        classify=Depends(get_family_classifier)):
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
def check_duplicate(name: str, house: str = "", session: Session = Depends(get_session)):
    dup = repo.find_duplicate(session, name, house)
    return {"duplicate": dup is not None, "id": dup.id if dup else None}

@app.get("/api/perfumes")
def list_perfumes(q: str | None = None, family: str | None = None,
                  fmt: str | None = None, session: Session = Depends(get_session)):
    if q or family or fmt:
        return queries.search_perfumes(session, q=q, family=family, fmt=fmt)
    return repo.list_perfumes(session)

@app.get("/api/perfumes/{perfume_id}")
def get_perfume(perfume_id: int, session: Session = Depends(get_session)):
    p = repo.get_perfume(session, perfume_id)
    if not p:
        raise HTTPException(404, "Perfume not found")
    return p

@app.patch("/api/perfumes/{perfume_id}")
def update_perfume(perfume_id: int, data: PerfumeUpdate,
                   session: Session = Depends(get_session)):
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
    return [{"id": n.id, "name": n.name, "family": n.family, "description": n.description,
             "origin": n.origin, "production": n.production}
            for n in repo.list_notes(session)]

@app.post("/api/notes/enrich-missing")
def enrich_missing_notes(session: Session = Depends(get_session),
                         enrich=Depends(get_note_enricher)):
    names = [n.name for n in repo.notes_missing_enrichment(session)]
    mapping: dict[str, dict] = {}
    for i in range(0, len(names), DESCRIBE_CHUNK):
        chunk = names[i:i + DESCRIBE_CHUNK]
        try:
            mapping.update(enrich(chunk))
        except LookupError:
            continue  # skip a failed chunk; others still apply
    updated = repo.apply_note_enrichment(session, mapping)
    return {"updated": updated}

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
        "perfumes": [{"id": p.id, "name": p.name, "house": p.house} for p in perfumes],
    }

@app.get("/api/insights/notes")
def insight_notes(session: Session = Depends(get_session)):
    return [{"note": name, "count": c} for name, c in queries.note_frequency(session)]

@app.get("/api/insights/families")
def insight_families(session: Session = Depends(get_session)):
    return [{"family": f, "count": c} for f, c in queries.family_breakdown(session)]

@app.get("/api/insights/formats")
def insight_formats(session: Session = Depends(get_session)):
    return queries.format_breakdown(session)

@app.get("/api/insights/similar")
def insight_similar(session: Session = Depends(get_session)):
    return queries.similar_pairs(session)
