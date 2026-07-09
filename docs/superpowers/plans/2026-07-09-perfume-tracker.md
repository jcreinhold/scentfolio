# Perfume Tracker (Scentfolio) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-first web app to catalogue a personal perfume collection, auto-populating notes/perfumer/house/family via a Claude web-search agent, with search-by-note, insights, and a note glossary.

**Architecture:** FastAPI + SQLAlchemy + SQLite backend serving a JSON API and running the lookup agent; React + Vite frontend consuming that API. Notes are normalized into their own table so "which perfumes have this note" and the glossary are direct joins. Backend is built and fully testable before the frontend starts.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, SQLite, `anthropic` SDK (Claude + built-in web search tool), pytest; React 18, Vite, TypeScript, Recharts, Vitest + React Testing Library.

**Conventions:**
- Backend lives in `backend/`, frontend in `frontend/`.
- Run backend commands from `backend/` with the venv active. Run frontend commands from `frontend/`.
- Scent family taxonomy (fixed enum used for classification & filtering): `Citrus`, `Floral`, `Woody`, `Oriental`, `Fresh`, `Aromatic`, `Fougere`, `Chypre`, `Gourmand`, `Leather`, `Other`.
- Formats enum: `full`, `travel`, `sample`.
- Note tiers enum: `top`, `heart`, `base`.

---

## Phase 1 — Backend

### Task 1: Backend scaffold + health endpoint

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_health.py`
- Create: `backend/pytest.ini`

- [ ] **Step 1: Create requirements and install**

`backend/requirements.txt`:
```
fastapi==0.115.*
uvicorn[standard]==0.32.*
sqlalchemy==2.0.*
pydantic==2.*
anthropic==0.40.*
python-dotenv==1.*
httpx==0.27.*
pytest==8.*
```

Run:
```bash
cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

- [ ] **Step 2: Write the failing test**

`backend/pytest.ini`:
```ini
[pytest]
pythonpath = .
```

`backend/tests/test_health.py`:
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_returns_ok():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_health.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.main'`.

- [ ] **Step 4: Write minimal implementation**

`backend/app/__init__.py`: empty file.
`backend/tests/__init__.py`: empty file.
`backend/app/main.py`:
```python
from fastapi import FastAPI

app = FastAPI(title="Scentfolio")

@app.get("/api/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_health.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/ && git commit -m "feat: backend scaffold with health endpoint"
```

---

### Task 2: Database engine + session

**Files:**
- Create: `backend/app/db.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_db.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_db.py`:
```python
from sqlalchemy import text
from app.db import Base, make_engine, make_sessionmaker

def test_engine_creates_tables_and_session_queries():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = make_sessionmaker(engine)
    with Session() as s:
        assert s.execute(text("SELECT 1")).scalar() == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_db.py -v`
Expected: FAIL — `No module named 'app.db'`.

- [ ] **Step 3: Write minimal implementation**

`backend/app/db.py`:
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

class Base(DeclarativeBase):
    pass

def make_engine(url: str = "sqlite:///scentfolio.db"):
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)

def make_sessionmaker(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
```

- [ ] **Step 4: Add shared test fixtures**

`backend/tests/conftest.py`:
```python
import pytest
from app.db import Base, make_engine, make_sessionmaker

@pytest.fixture
def session():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = make_sessionmaker(engine)
    with Session() as s:
        yield s
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_db.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/ && git commit -m "feat: database engine and session factory"
```

---

### Task 3: ORM models (Perfume, Note, PerfumeNote)

**Files:**
- Create: `backend/app/models.py`
- Create: `backend/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_models.py`:
```python
from app.models import Perfume, Note, PerfumeNote

def test_perfume_note_relationship(session):
    note = Note(name="bergamot", family="Citrus")
    perfume = Perfume(name="Sauvage", house="Dior", year=2015,
                      scent_family="Fresh", formats="full,sample")
    session.add_all([note, perfume])
    session.flush()
    session.add(PerfumeNote(perfume_id=perfume.id, note_id=note.id, tier="top"))
    session.commit()

    reloaded = session.get(Perfume, perfume.id)
    assert reloaded.perfume_notes[0].note.name == "bergamot"
    assert reloaded.perfume_notes[0].tier == "top"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL — `No module named 'app.models'`.

- [ ] **Step 3: Write minimal implementation**

`backend/app/models.py`:
```python
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

def _now():
    return datetime.now(timezone.utc)

class Perfume(Base):
    __tablename__ = "perfumes"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    house: Mapped[str] = mapped_column(String(200), default="")
    perfumer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scent_family: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    my_impressions: Mapped[str] = mapped_column(Text, default="")
    formats: Mapped[str] = mapped_column(String(50), default="")  # comma-joined
    source_urls: Mapped[str] = mapped_column(Text, default="")     # newline-joined
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    perfume_notes: Mapped[list["PerfumeNote"]] = relationship(
        back_populates="perfume", cascade="all, delete-orphan")

class Note(Base):
    __tablename__ = "notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    family: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    perfume_notes: Mapped[list["PerfumeNote"]] = relationship(back_populates="note")

class PerfumeNote(Base):
    __tablename__ = "perfume_notes"
    perfume_id: Mapped[int] = mapped_column(ForeignKey("perfumes.id"), primary_key=True)
    note_id: Mapped[int] = mapped_column(ForeignKey("notes.id"), primary_key=True)
    tier: Mapped[str] = mapped_column(String(10), primary_key=True)
    perfume: Mapped["Perfume"] = relationship(back_populates="perfume_notes")
    note: Mapped["Note"] = relationship(back_populates="perfume_notes")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/ && git commit -m "feat: ORM models for perfumes, notes, and join"
```

---

### Task 4: Pydantic schemas

**Files:**
- Create: `backend/app/schemas.py`
- Create: `backend/tests/test_schemas.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_schemas.py`:
```python
import pytest
from pydantic import ValidationError
from app.schemas import PerfumeCreate, NoteInput

def test_perfume_create_validates_format_and_family():
    p = PerfumeCreate(name="Aventus", house="Creed", scent_family="Chypre",
                      formats=["full", "sample"],
                      notes=[NoteInput(name="bergamot", tier="top")])
    assert p.formats == ["full", "sample"]

def test_invalid_format_rejected():
    with pytest.raises(ValidationError):
        PerfumeCreate(name="X", formats=["gigantic"])

def test_invalid_tier_rejected():
    with pytest.raises(ValidationError):
        NoteInput(name="rose", tier="middle")  # must be top/heart/base
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_schemas.py -v`
Expected: FAIL — `No module named 'app.schemas'`.

- [ ] **Step 3: Write minimal implementation**

`backend/app/schemas.py`:
```python
from typing import Literal
from pydantic import BaseModel, Field

Tier = Literal["top", "heart", "base"]
Format = Literal["full", "travel", "sample"]
Family = Literal["Citrus", "Floral", "Woody", "Oriental", "Fresh", "Aromatic",
                 "Fougere", "Chypre", "Gourmand", "Leather", "Other"]

class NoteInput(BaseModel):
    name: str
    tier: Tier
    family: str | None = None

class PerfumeCreate(BaseModel):
    name: str
    house: str = ""
    perfumer: str | None = None
    year: int | None = None
    scent_family: Family | None = None
    description: str = ""
    my_impressions: str = ""
    formats: list[Format] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    notes: list[NoteInput] = Field(default_factory=list)

class PerfumeUpdate(BaseModel):
    my_impressions: str | None = None
    formats: list[Format] | None = None

class NoteOut(BaseModel):
    id: int
    name: str
    tier: Tier | None = None
    family: str | None = None

class PerfumeOut(BaseModel):
    id: int
    name: str
    house: str
    perfumer: str | None
    year: int | None
    scent_family: str | None
    description: str
    my_impressions: str
    formats: list[str]
    source_urls: list[str]
    notes: list[NoteOut]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_schemas.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/ && git commit -m "feat: pydantic schemas for perfume I/O"
```

---

### Task 5: Repository layer with note normalization

**Files:**
- Create: `backend/app/repository.py`
- Create: `backend/tests/test_repository.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_repository.py`:
```python
from app import repository as repo
from app.schemas import PerfumeCreate, NoteInput

def _sample(name="Sauvage", house="Dior"):
    return PerfumeCreate(name=name, house=house, scent_family="Fresh",
                         formats=["full"],
                         notes=[NoteInput(name="Bergamot", tier="top", family="Citrus"),
                                NoteInput(name="ambroxan", tier="base")])

def test_create_normalizes_and_dedupes_notes(session):
    repo.create_perfume(session, _sample())
    repo.create_perfume(session, _sample(name="Homme", house="Dior"))
    # "Bergamot" and "bergamot" should be ONE note row (normalized lowercase)
    all_notes = repo.list_notes(session)
    names = [n.name for n in all_notes]
    assert names.count("bergamot") == 1

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_repository.py -v`
Expected: FAIL — `No module named 'app.repository'`.

- [ ] **Step 3: Write minimal implementation**

`backend/app/repository.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_repository.py -v`
Expected: PASS (all three tests).

- [ ] **Step 5: Commit**

```bash
git add backend/ && git commit -m "feat: repository layer with normalized notes"
```

---

### Task 6: Search & insights queries

**Files:**
- Create: `backend/app/queries.py`
- Create: `backend/tests/test_queries.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_queries.py`:
```python
from app import repository as repo, queries
from app.schemas import PerfumeCreate, NoteInput

def _seed(session):
    repo.create_perfume(session, PerfumeCreate(
        name="Sauvage", house="Dior", scent_family="Fresh", formats=["full"],
        notes=[NoteInput(name="bergamot", tier="top"), NoteInput(name="ambroxan", tier="base")]))
    repo.create_perfume(session, PerfumeCreate(
        name="Aventus", house="Creed", scent_family="Chypre", formats=["sample"],
        notes=[NoteInput(name="bergamot", tier="top"), NoteInput(name="birch", tier="heart")]))

def test_search_matches_name_or_note(session):
    _seed(session)
    by_name = queries.search_perfumes(session, q="aven")
    assert [p.name for p in by_name] == ["Aventus"]
    by_note = queries.search_perfumes(session, q="bergamot")
    assert {p.name for p in by_note} == {"Sauvage", "Aventus"}

def test_filter_by_family_and_format(session):
    _seed(session)
    fam = queries.search_perfumes(session, family="Chypre")
    assert [p.name for p in fam] == ["Aventus"]
    fmt = queries.search_perfumes(session, fmt="full")
    assert [p.name for p in fmt] == ["Sauvage"]

def test_note_frequency(session):
    _seed(session)
    freq = dict(queries.note_frequency(session))
    assert freq["bergamot"] == 2
    assert freq["birch"] == 1

def test_family_breakdown(session):
    _seed(session)
    fams = dict(queries.family_breakdown(session))
    assert fams["Fresh"] == 1 and fams["Chypre"] == 1

def test_similarity_shared_notes(session):
    _seed(session)
    pairs = queries.similar_pairs(session)
    # Sauvage & Aventus share bergamot -> one pair with shared count 1
    assert pairs[0]["shared"] == ["bergamot"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_queries.py -v`
Expected: FAIL — `No module named 'app.queries'`.

- [ ] **Step 3: Write minimal implementation**

`backend/app/queries.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_queries.py -v`
Expected: PASS (all five tests).

- [ ] **Step 5: Commit**

```bash
git add backend/ && git commit -m "feat: search and insight queries"
```

---

### Task 7: Lookup agent (Claude + web search) with mocked tests

**Files:**
- Create: `backend/app/agent.py`
- Create: `backend/tests/test_agent.py`

- [ ] **Step 1: Write the failing test**

The agent must be testable without hitting the network. We inject the Anthropic client, and the agent parses a tool-call/JSON result into a `PerfumeCreate` draft.

`backend/tests/test_agent.py`:
```python
import json
import pytest
from app.agent import extract_draft, LookupError

def _fake_response(payload: dict):
    # Mimics the shape agent.extract_draft expects: a JSON string of the draft.
    return json.dumps(payload)

def test_extract_draft_parses_valid_payload():
    raw = _fake_response({
        "name": "Aventus", "house": "Creed", "perfumer": "Olivier Creed",
        "year": 2010, "scent_family": "Chypre",
        "description": "Fruity smoky signature scent.",
        "source_urls": ["https://www.fragrantica.com/perfume/x"],
        "notes": [{"name": "pineapple", "tier": "top"},
                  {"name": "birch", "tier": "heart", "family": "Woody"}],
        "confidence": "high"})
    draft = extract_draft(raw)
    assert draft.perfume.name == "Aventus"
    assert draft.confidence == "high"
    assert draft.perfume.notes[0].name == "pineapple"

def test_extract_draft_coerces_unknown_family_to_other():
    raw = _fake_response({"name": "X", "scent_family": "Spacewood", "notes": []})
    draft = extract_draft(raw)
    assert draft.perfume.scent_family == "Other"

def test_extract_draft_rejects_non_json():
    with pytest.raises(LookupError):
        extract_draft("I could not find this perfume.")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_agent.py -v`
Expected: FAIL — `No module named 'app.agent'`.

- [ ] **Step 3: Write minimal implementation**

`backend/app/agent.py`:
```python
import json
import os
from typing import Literal
from pydantic import BaseModel, ValidationError
from app.schemas import PerfumeCreate

VALID_FAMILIES = {"Citrus", "Floral", "Woody", "Oriental", "Fresh", "Aromatic",
                  "Fougere", "Chypre", "Gourmand", "Leather", "Other"}

class LookupError(Exception):
    pass

class Draft(BaseModel):
    perfume: PerfumeCreate
    confidence: Literal["high", "medium", "low"] = "medium"

SYSTEM_PROMPT = (
    "You are a fragrance research assistant. Given a perfume name, use web search to "
    "find its details on Fragrantica and the brand's official site. Return ONLY a JSON "
    "object (no prose) with keys: name, house, perfumer, year, scent_family, "
    "description, source_urls (list), notes (list of {name, tier one of "
    "top/heart/base, family}), confidence (high/medium/low). scent_family must be one "
    f"of: {sorted(VALID_FAMILIES)}. If unsure of a field use null."
)

def extract_draft(raw_text: str) -> Draft:
    """Parse the model's JSON text into a validated Draft."""
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise LookupError(f"Model did not return JSON: {raw_text[:200]}") from e
    if payload.get("scent_family") not in VALID_FAMILIES:
        payload["scent_family"] = "Other" if payload.get("scent_family") else None
    # Drop notes with invalid tiers rather than failing the whole lookup.
    payload["notes"] = [n for n in payload.get("notes", [])
                        if n.get("tier") in ("top", "heart", "base")]
    confidence = payload.pop("confidence", "medium")
    try:
        perfume = PerfumeCreate(**payload)
    except ValidationError as e:
        raise LookupError(str(e)) from e
    return Draft(perfume=perfume, confidence=confidence)

def lookup(name: str, client=None) -> Draft:
    """Live lookup via Claude web search. `client` injectable for tests."""
    if client is None:
        from anthropic import Anthropic
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise LookupError("ANTHROPIC_API_KEY not set")
        client = Anthropic()
    resp = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": f"Look up the perfume: {name}"}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    return extract_draft(text)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_agent.py -v`
Expected: PASS (all three tests). `lookup()` is not exercised (no network).

- [ ] **Step 5: Commit**

```bash
git add backend/ && git commit -m "feat: lookup agent with injectable client and JSON parsing"
```

---

### Task 8: API routes wiring

**Files:**
- Modify: `backend/app/main.py`
- Create: `backend/app/deps.py`
- Create: `backend/tests/test_api.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_api.py`:
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app, get_session
from app.db import Base, make_engine, make_sessionmaker

@pytest.fixture
def client():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = make_sessionmaker(engine)
    def _override():
        with Session() as s:
            yield s
    app.dependency_overrides[get_session] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()

def _create(client, name="Sauvage", house="Dior", family="Fresh"):
    return client.post("/api/perfumes", json={
        "name": name, "house": house, "scent_family": family, "formats": ["full"],
        "notes": [{"name": "bergamot", "tier": "top"}]})

def test_create_and_get_perfume(client):
    r = _create(client)
    assert r.status_code == 201
    pid = r.json()["id"]
    got = client.get(f"/api/perfumes/{pid}")
    assert got.json()["notes"][0]["name"] == "bergamot"

def test_search_by_note(client):
    _create(client)
    r = client.get("/api/perfumes", params={"q": "bergamot"})
    assert [p["name"] for p in r.json()] == ["Sauvage"]

def test_note_detail_lists_perfumes(client):
    _create(client)
    r = client.get("/api/notes/bergamot")
    assert r.status_code == 200
    assert [p["name"] for p in r.json()["perfumes"]] == ["Sauvage"]

def test_insights_endpoints(client):
    _create(client)
    assert client.get("/api/insights/notes").status_code == 200
    assert client.get("/api/insights/families").status_code == 200
    assert client.get("/api/insights/similar").status_code == 200

def test_update_impressions(client):
    pid = _create(client).json()["id"]
    r = client.patch(f"/api/perfumes/{pid}", json={"my_impressions": "Great!"})
    assert r.json()["my_impressions"] == "Great!"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api.py -v`
Expected: FAIL — `ImportError: cannot import name 'get_session'`.

- [ ] **Step 3: Write dependency provider**

`backend/app/deps.py`:
```python
from app.db import Base, make_engine, make_sessionmaker

_engine = make_engine()
Base.metadata.create_all(_engine)
_Session = make_sessionmaker(_engine)

def get_session():
    with _Session() as s:
        yield s
```

- [ ] **Step 4: Rewrite `main.py` with routes**

`backend/app/main.py`:
```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.deps import get_session
from app import repository as repo, queries
from app.schemas import PerfumeCreate, PerfumeUpdate

app = FastAPI(title="Scentfolio")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
                   allow_methods=["*"], allow_headers=["*"])

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.post("/api/perfumes", status_code=201)
def create_perfume(data: PerfumeCreate, session: Session = Depends(get_session)):
    return repo.create_perfume(session, data)

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
    return [{"id": n.id, "name": n.name, "family": n.family} for n in repo.list_notes(session)]

@app.get("/api/notes/{note_name}")
def note_detail(note_name: str, session: Session = Depends(get_session)):
    notes = {n.name: n for n in repo.list_notes(session)}
    n = notes.get(note_name.strip().lower())
    perfumes = repo.perfumes_with_note(session, note_name)
    return {
        "name": note_name.strip().lower(),
        "family": n.family if n else None,
        "description": n.description if n else "",
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_api.py -v`
Expected: PASS (all five tests).

- [ ] **Step 6: Commit**

```bash
git add backend/ && git commit -m "feat: REST API routes for perfumes, notes, insights"
```

---

### Task 9: Lookup endpoint + duplicate warning

**Files:**
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_lookup_api.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_lookup_api.py`:
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app, get_session, get_lookup
from app.db import Base, make_engine, make_sessionmaker
from app.agent import Draft
from app.schemas import PerfumeCreate, NoteInput

@pytest.fixture
def client():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = make_sessionmaker(engine)
    def _sess():
        with Session() as s:
            yield s
    def _fake_lookup(name: str):
        return Draft(perfume=PerfumeCreate(name="Aventus", house="Creed",
                     scent_family="Chypre",
                     notes=[NoteInput(name="bergamot", tier="top")]),
                     confidence="high")
    app.dependency_overrides[get_session] = _sess
    app.dependency_overrides[get_lookup] = lambda: _fake_lookup
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_lookup_returns_draft(client):
    r = client.post("/api/lookup", json={"name": "Aventus"})
    assert r.status_code == 200
    body = r.json()
    assert body["confidence"] == "high"
    assert body["perfume"]["name"] == "Aventus"

def test_duplicate_flag_on_create(client):
    client.post("/api/perfumes", json={"name": "Aventus", "house": "Creed", "notes": []})
    r = client.get("/api/perfumes/check-duplicate", params={"name": "Aventus", "house": "Creed"})
    assert r.json()["duplicate"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_lookup_api.py -v`
Expected: FAIL — `cannot import name 'get_lookup'`.

- [ ] **Step 3: Add lookup dependency + endpoints to `main.py`**

Add near the top of `backend/app/main.py` (after existing imports):
```python
from pydantic import BaseModel
from app.agent import lookup as live_lookup, LookupError

class LookupRequest(BaseModel):
    name: str

def get_lookup():
    return live_lookup
```

Add these endpoints to `backend/app/main.py`:
```python
@app.post("/api/lookup")
def lookup_perfume(req: LookupRequest, lookup=Depends(get_lookup)):
    try:
        draft = lookup(req.name)
    except LookupError as e:
        raise HTTPException(422, f"Lookup failed: {e}")
    return draft.model_dump()

@app.get("/api/perfumes/check-duplicate")
def check_duplicate(name: str, house: str = "", session: Session = Depends(get_session)):
    dup = repo.find_duplicate(session, name, house)
    return {"duplicate": dup is not None, "id": dup.id if dup else None}
```

> Note: define `/api/perfumes/check-duplicate` BEFORE `/api/perfumes/{perfume_id}` in the file so the literal path wins over the path param.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_lookup_api.py -v`
Expected: PASS (both tests).

- [ ] **Step 5: Run the full backend suite**

Run: `pytest -v`
Expected: ALL tests across all files PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/ && git commit -m "feat: lookup endpoint and duplicate check"
```

---

### Task 10: Env config + run script + manual smoke test

**Files:**
- Create: `backend/.env.example`
- Create: `backend/run.sh`
- Modify: `backend/app/agent.py` (load dotenv)

- [ ] **Step 1: Add env example and dotenv loading**

`backend/.env.example`:
```
ANTHROPIC_API_KEY=sk-ant-...
```

At the top of `backend/app/agent.py`, add after imports:
```python
from dotenv import load_dotenv
load_dotenv()
```

- [ ] **Step 2: Add run script**

`backend/run.sh`:
```bash
#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```
Run: `chmod +x backend/run.sh`

- [ ] **Step 3: Manual smoke test (real lookup)**

Create `backend/.env` from the example with a real key, then:
```bash
./backend/run.sh
# in another terminal:
curl -s -X POST localhost:8000/api/lookup -H 'content-type: application/json' \
  -d '{"name":"Dior Sauvage"}' | python3 -m json.tool
```
Expected: JSON draft with notes, house "Dior", and source_urls. If it fails, the response says why (missing key, no JSON) — do not proceed until this returns a real draft.

- [ ] **Step 4: Commit**

```bash
git add backend/ && git commit -m "chore: env config and backend run script"
```

---

## Phase 2 — Frontend

### Task 11: Frontend scaffold + API client + types

**Files:**
- Create: `frontend/` (Vite React-TS scaffold)
- Create: `frontend/src/api.ts`
- Create: `frontend/src/types.ts`
- Create: `frontend/src/api.test.ts`
- Modify: `frontend/vite.config.ts`

- [ ] **Step 1: Scaffold Vite app**

Run:
```bash
cd /Users/tshiu/code/perfume-tracker && npm create vite@latest frontend -- --template react-ts
cd frontend && npm install && npm install recharts && npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
```

- [ ] **Step 2: Configure Vitest + proxy**

`frontend/vite.config.ts`:
```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://localhost:8000" } },
  test: { environment: "jsdom", globals: true },
});
```

- [ ] **Step 3: Write the failing test**

`frontend/src/types.ts`:
```ts
export type Tier = "top" | "heart" | "base";
export type Format = "full" | "travel" | "sample";

export interface Note { id: number; name: string; tier?: Tier; family?: string | null; }
export interface Perfume {
  id: number; name: string; house: string; perfumer: string | null;
  year: number | null; scent_family: string | null; description: string;
  my_impressions: string; formats: string[]; source_urls: string[]; notes: Note[];
}
export interface Draft { perfume: Omit<Perfume, "id">; confidence: "high" | "medium" | "low"; }
```

`frontend/src/api.test.ts`:
```ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { listPerfumes, lookupPerfume } from "./api";

beforeEach(() => {
  global.fetch = vi.fn();
});

it("listPerfumes builds query string from filters", async () => {
  (global.fetch as any).mockResolvedValue({ ok: true, json: async () => [] });
  await listPerfumes({ q: "bergamot", family: "Fresh" });
  const url = (global.fetch as any).mock.calls[0][0];
  expect(url).toContain("q=bergamot");
  expect(url).toContain("family=Fresh");
});

it("lookupPerfume posts the name", async () => {
  (global.fetch as any).mockResolvedValue({ ok: true, json: async () => ({ confidence: "high" }) });
  const d = await lookupPerfume("Aventus");
  expect(d.confidence).toBe("high");
});
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/api.test.ts`
Expected: FAIL — cannot find `./api`.

- [ ] **Step 5: Write minimal implementation**

`frontend/src/api.ts`:
```ts
import type { Perfume, Draft } from "./types";

async function getJSON<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`GET ${url} failed: ${r.status}`);
  return r.json();
}

export async function listPerfumes(
  filters: { q?: string; family?: string; fmt?: string } = {}
): Promise<Perfume[]> {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.family) params.set("family", filters.family);
  if (filters.fmt) params.set("fmt", filters.fmt);
  const qs = params.toString();
  return getJSON(`/api/perfumes${qs ? `?${qs}` : ""}`);
}

export const getPerfume = (id: number) => getJSON<Perfume>(`/api/perfumes/${id}`);

export async function lookupPerfume(name: string): Promise<Draft> {
  const r = await fetch("/api/lookup", {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!r.ok) throw new Error((await r.json()).detail ?? "Lookup failed");
  return r.json();
}

export async function createPerfume(draft: Draft["perfume"]): Promise<Perfume> {
  const r = await fetch("/api/perfumes", {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify(draft),
  });
  if (!r.ok) throw new Error("Create failed");
  return r.json();
}

export async function updatePerfume(
  id: number, patch: { my_impressions?: string; formats?: string[] }
): Promise<Perfume> {
  const r = await fetch(`/api/perfumes/${id}`, {
    method: "PATCH", headers: { "content-type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!r.ok) throw new Error("Update failed");
  return r.json();
}

export const getNote = (name: string) =>
  getJSON<{ name: string; family: string | null; description: string;
            perfumes: { id: number; name: string; house: string }[] }>(
    `/api/notes/${encodeURIComponent(name)}`);
export const listNotes = () => getJSON<{ id: number; name: string; family: string | null }[]>(`/api/notes`);
export const insightNotes = () => getJSON<{ note: string; count: number }[]>(`/api/insights/notes`);
export const insightFamilies = () => getJSON<{ family: string; count: number }[]>(`/api/insights/families`);
export const insightSimilar = () => getJSON<{ a: string; b: string; shared: string[]; count: number }[]>(`/api/insights/similar`);
```

- [ ] **Step 6: Run test to verify it passes**

Run: `npx vitest run src/api.test.ts`
Expected: PASS (both tests).

- [ ] **Step 7: Commit**

```bash
git add frontend/ && git commit -m "feat: frontend scaffold, types, and API client"
```

---

### Task 12: App shell + routing + Collection view

**Files:**
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/components/PerfumeCard.tsx`
- Create: `frontend/src/views/Collection.tsx`
- Create: `frontend/src/views/Collection.test.tsx`
- Create: `frontend/src/styles.css`
- Modify: `frontend/src/main.tsx`
- Install: `react-router-dom`

- [ ] **Step 1: Install router**

Run: `cd frontend && npm install react-router-dom`

- [ ] **Step 2: Write the failing test**

`frontend/src/views/Collection.test.tsx`:
```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi } from "vitest";
import Collection from "./Collection";
import * as api from "../api";

it("renders perfume cards from the API", async () => {
  vi.spyOn(api, "listPerfumes").mockResolvedValue([{
    id: 1, name: "Sauvage", house: "Dior", perfumer: null, year: 2015,
    scent_family: "Fresh", description: "", my_impressions: "",
    formats: ["full"], source_urls: [], notes: [{ id: 1, name: "bergamot", tier: "top" }],
  }]);
  render(<MemoryRouter><Collection /></MemoryRouter>);
  await waitFor(() => expect(screen.getByText("Sauvage")).toBeInTheDocument());
  expect(screen.getByText("bergamot")).toBeInTheDocument();
});
```

Add `frontend/src/setupTests.ts`:
```ts
import "@testing-library/jest-dom";
```
And add to `vite.config.ts` `test` block: `setupFiles: "./src/setupTests.ts",`.

- [ ] **Step 3: Run test to verify it fails**

Run: `npx vitest run src/views/Collection.test.tsx`
Expected: FAIL — cannot find `./Collection`.

- [ ] **Step 4: Write minimal implementation**

`frontend/src/components/PerfumeCard.tsx`:
```tsx
import { Link } from "react-router-dom";
import type { Perfume } from "../types";

export default function PerfumeCard({ p }: { p: Perfume }) {
  return (
    <Link to={`/perfume/${p.id}`} className="card">
      <div className="card-top">
        <span className="card-name">{p.name}</span>
        {p.formats.map((f) => <span key={f} className={`badge badge-${f}`}>{f}</span>)}
      </div>
      <div className="card-sub">{p.house}{p.year ? ` · ${p.year}` : ""}</div>
      <div className="card-notes">
        {p.notes.slice(0, 3).map((n) => <span key={n.id} className="chip">{n.name}</span>)}
      </div>
    </Link>
  );
}
```

`frontend/src/views/Collection.tsx`:
```tsx
import { useEffect, useState } from "react";
import { listPerfumes } from "../api";
import type { Perfume } from "../types";
import PerfumeCard from "../components/PerfumeCard";

const FAMILIES = ["Citrus","Floral","Woody","Oriental","Fresh","Aromatic",
  "Fougere","Chypre","Gourmand","Leather","Other"];

export default function Collection() {
  const [perfumes, setPerfumes] = useState<Perfume[]>([]);
  const [q, setQ] = useState("");
  const [family, setFamily] = useState("");
  const [fmt, setFmt] = useState("");

  useEffect(() => {
    listPerfumes({ q: q || undefined, family: family || undefined, fmt: fmt || undefined })
      .then(setPerfumes);
  }, [q, family, fmt]);

  return (
    <div>
      <input className="search" placeholder="Search names or notes…"
             value={q} onChange={(e) => setQ(e.target.value)} />
      <div className="filters">
        <select value={family} onChange={(e) => setFamily(e.target.value)}>
          <option value="">All families</option>
          {FAMILIES.map((f) => <option key={f} value={f}>{f}</option>)}
        </select>
        <select value={fmt} onChange={(e) => setFmt(e.target.value)}>
          <option value="">All formats</option>
          <option value="full">Full</option>
          <option value="travel">Travel</option>
          <option value="sample">Sample</option>
        </select>
      </div>
      <div className="grid">
        {perfumes.map((p) => <PerfumeCard key={p.id} p={p} />)}
      </div>
    </div>
  );
}
```

`frontend/src/App.tsx`:
```tsx
import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import Collection from "./views/Collection";
import PerfumeDetail from "./views/PerfumeDetail";
import Add from "./views/Add";
import Glossary from "./views/Glossary";
import NoteDetail from "./views/NoteDetail";
import Insights from "./views/Insights";
import "./styles.css";

export default function App() {
  return (
    <BrowserRouter>
      <div className="layout">
        <nav className="sidebar">
          <div className="brand">🧴 Scentfolio</div>
          <NavLink to="/">Collection</NavLink>
          <NavLink to="/add">Add</NavLink>
          <NavLink to="/insights">Insights</NavLink>
          <NavLink to="/glossary">Note Glossary</NavLink>
        </nav>
        <main className="content">
          <Routes>
            <Route path="/" element={<Collection />} />
            <Route path="/add" element={<Add />} />
            <Route path="/perfume/:id" element={<PerfumeDetail />} />
            <Route path="/insights" element={<Insights />} />
            <Route path="/glossary" element={<Glossary />} />
            <Route path="/note/:name" element={<NoteDetail />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
```

`frontend/src/main.tsx`:
```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
```

`frontend/src/styles.css`:
```css
* { box-sizing: border-box; }
body { margin: 0; font-family: system-ui, sans-serif; color: #1a1a1a; }
.layout { display: flex; min-height: 100vh; }
.sidebar { width: 180px; background: #1a1a1a; color: #eee; padding: 20px 14px; }
.sidebar .brand { font-weight: 700; margin-bottom: 20px; }
.sidebar a { display: block; color: #ccc; text-decoration: none; padding: 8px 10px;
  border-radius: 6px; margin-bottom: 4px; }
.sidebar a.active { background: #333; color: #fff; }
.content { flex: 1; padding: 24px; max-width: 900px; }
.search { width: 100%; padding: 10px; font-size: 15px; border: 1px solid #ccc; border-radius: 8px; }
.filters { display: flex; gap: 8px; margin: 12px 0; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
.card { display: block; border: 1px solid #ddd; border-radius: 10px; padding: 12px; text-decoration: none; color: inherit; }
.card-top { display: flex; justify-content: space-between; align-items: start; }
.card-name { font-weight: 600; }
.card-sub { font-size: 12px; opacity: .6; }
.card-notes { margin-top: 8px; display: flex; gap: 4px; flex-wrap: wrap; }
.chip { font-size: 10px; background: #eef; padding: 2px 8px; border-radius: 10px; }
.badge { font-size: 9px; padding: 2px 6px; border-radius: 10px; color: #fff; text-transform: uppercase; }
.badge-full { background: #1a1a1a; } .badge-travel { background: #0ea5a0; } .badge-sample { background: #7c5cff; }
.pyramid div { padding: 8px 12px; margin-bottom: 4px; border-left: 3px solid; }
.pyramid .top { background: #f5f0ff; border-color: #a78bfa; }
.pyramid .heart { background: #fff5f0; border-color: #fb923c; }
.pyramid .base { background: #f0fff5; border-color: #34d399; }
.label { font-size: 11px; letter-spacing: .5px; text-transform: uppercase; opacity: .6; margin-top: 16px; }
```

- [ ] **Step 5: Create placeholder views so the app compiles**

Create minimal stubs (fleshed out in later tasks) so imports in `App.tsx` resolve:
`frontend/src/views/Add.tsx`, `PerfumeDetail.tsx`, `Glossary.tsx`, `NoteDetail.tsx`, `Insights.tsx`, each:
```tsx
export default function Placeholder() { return <div>Coming soon</div>; }
```
(Name each function distinctly, e.g. `Add`, `PerfumeDetail`, etc.)

- [ ] **Step 6: Run test to verify it passes**

Run: `npx vitest run src/views/Collection.test.tsx`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/ && git commit -m "feat: app shell, routing, and collection view"
```

---

### Task 13: Add / lookup flow with confirmation

**Files:**
- Modify: `frontend/src/views/Add.tsx`
- Create: `frontend/src/views/Add.test.tsx`

- [ ] **Step 1: Write the failing test**

`frontend/src/views/Add.test.tsx`:
```tsx
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi, it, expect } from "vitest";
import Add from "./Add";
import * as api from "../api";

it("looks up a name and shows the draft for confirmation", async () => {
  vi.spyOn(api, "lookupPerfume").mockResolvedValue({
    confidence: "high",
    perfume: { name: "Aventus", house: "Creed", perfumer: "Olivier Creed", year: 2010,
      scent_family: "Chypre", description: "Smoky.", my_impressions: "",
      formats: [], source_urls: ["https://x"], notes: [{ id: 0, name: "bergamot", tier: "top" }] },
  } as any);

  render(<MemoryRouter><Add /></MemoryRouter>);
  fireEvent.change(screen.getByPlaceholderText(/perfume by name/i), { target: { value: "Aventus" } });
  fireEvent.click(screen.getByText(/look up/i));

  await waitFor(() => expect(screen.getByDisplayValue("Aventus")).toBeInTheDocument());
  expect(screen.getByText(/high confidence/i)).toBeInTheDocument();
  expect(screen.getByText("bergamot")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/views/Add.test.tsx`
Expected: FAIL — placeholder Add renders "Coming soon".

- [ ] **Step 3: Write minimal implementation**

`frontend/src/views/Add.tsx`:
```tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { lookupPerfume, createPerfume } from "../api";
import type { Draft, Format } from "../types";

const FORMATS: Format[] = ["full", "travel", "sample"];

export default function Add() {
  const [name, setName] = useState("");
  const [draft, setDraft] = useState<Draft | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const nav = useNavigate();

  async function doLookup() {
    setError(""); setLoading(true);
    try { setDraft(await lookupPerfume(name)); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }

  function patch(field: string, value: any) {
    if (!draft) return;
    setDraft({ ...draft, perfume: { ...draft.perfume, [field]: value } });
  }

  function toggleFormat(f: Format) {
    if (!draft) return;
    const has = draft.perfume.formats.includes(f);
    patch("formats", has ? draft.perfume.formats.filter((x) => x !== f)
                         : [...draft.perfume.formats, f]);
  }

  async function save() {
    if (!draft) return;
    const created = await createPerfume(draft.perfume);
    nav(`/perfume/${created.id}`);
  }

  return (
    <div>
      <h2>Add a perfume</h2>
      <div style={{ display: "flex", gap: 8 }}>
        <input className="search" placeholder="Add a perfume by name…"
               value={name} onChange={(e) => setName(e.target.value)} />
        <button onClick={doLookup} disabled={loading || !name}>
          {loading ? "Searching…" : "Look up"}
        </button>
      </div>
      {error && <p style={{ color: "crimson" }}>{error} — you can still add it manually below.</p>}

      {draft && (
        <div>
          <p className="label">{draft.confidence} confidence — verify against sources before saving</p>
          <input className="search" value={draft.perfume.name}
                 onChange={(e) => patch("name", e.target.value)} />
          <input className="search" value={draft.perfume.house}
                 onChange={(e) => patch("house", e.target.value)} placeholder="House" />
          <textarea className="search" value={draft.perfume.description}
                    onChange={(e) => patch("description", e.target.value)} />
          <div className="filters">
            {FORMATS.map((f) => (
              <label key={f}>
                <input type="checkbox" checked={draft.perfume.formats.includes(f)}
                       onChange={() => toggleFormat(f)} /> {f}
              </label>
            ))}
          </div>
          <div className="card-notes">
            {draft.perfume.notes.map((n, i) => <span key={i} className="chip">{n.name} ({n.tier})</span>)}
          </div>
          {draft.perfume.source_urls.map((u) => (
            <div key={u}><a href={u} target="_blank" rel="noreferrer">{u}</a></div>
          ))}
          <button onClick={save} style={{ marginTop: 12 }}>Save to collection</button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/views/Add.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/ && git commit -m "feat: add/lookup flow with editable draft confirmation"
```

---

### Task 14: Perfume detail (pyramid, formats, impressions)

**Files:**
- Modify: `frontend/src/views/PerfumeDetail.tsx`
- Create: `frontend/src/views/PerfumeDetail.test.tsx`

- [ ] **Step 1: Write the failing test**

`frontend/src/views/PerfumeDetail.test.tsx`:
```tsx
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { vi, it, expect } from "vitest";
import PerfumeDetail from "./PerfumeDetail";
import * as api from "../api";

const perfume = {
  id: 1, name: "Aventus", house: "Creed", perfumer: "Olivier Creed", year: 2010,
  scent_family: "Chypre", description: "Smoky.", my_impressions: "old note",
  formats: ["full"], source_urls: [], notes: [
    { id: 1, name: "bergamot", tier: "top" }, { id: 2, name: "birch", tier: "heart" }],
};

it("shows pyramid and saves impressions", async () => {
  vi.spyOn(api, "getPerfume").mockResolvedValue(perfume as any);
  const upd = vi.spyOn(api, "updatePerfume").mockResolvedValue({ ...perfume, my_impressions: "new" } as any);
  render(<MemoryRouter initialEntries={["/perfume/1"]}>
    <Routes><Route path="/perfume/:id" element={<PerfumeDetail />} /></Routes>
  </MemoryRouter>);
  await waitFor(() => expect(screen.getByText("Aventus")).toBeInTheDocument());
  expect(screen.getByText("bergamot")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText(/impressions/i), { target: { value: "new" } });
  fireEvent.click(screen.getByText(/save impressions/i));
  await waitFor(() => expect(upd).toHaveBeenCalledWith(1, { my_impressions: "new" }));
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/views/PerfumeDetail.test.tsx`
Expected: FAIL — placeholder renders "Coming soon".

- [ ] **Step 3: Write minimal implementation**

`frontend/src/views/PerfumeDetail.tsx`:
```tsx
import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getPerfume, updatePerfume } from "../api";
import type { Perfume, Tier } from "../types";

const TIERS: Tier[] = ["top", "heart", "base"];

export default function PerfumeDetail() {
  const { id } = useParams();
  const [p, setP] = useState<Perfume | null>(null);
  const [impressions, setImpressions] = useState("");

  useEffect(() => {
    getPerfume(Number(id)).then((data) => { setP(data); setImpressions(data.my_impressions); });
  }, [id]);

  if (!p) return <div>Loading…</div>;

  return (
    <div>
      <h2>{p.name}</h2>
      <div className="card-sub">{p.house}{p.year ? ` · ${p.year}` : ""}
        {p.perfumer ? ` · Perfumer: ${p.perfumer}` : ""}
        {p.scent_family ? ` · ${p.scent_family}` : ""}</div>

      <div className="label">Note pyramid</div>
      <div className="pyramid">
        {TIERS.map((tier) => (
          <div key={tier} className={tier}>
            <b>{tier}:</b>{" "}
            {p.notes.filter((n) => n.tier === tier).map((n, i, arr) => (
              <span key={n.id}>
                <Link to={`/note/${encodeURIComponent(n.name)}`}>{n.name}</Link>
                {i < arr.length - 1 ? ", " : ""}
              </span>
            ))}
          </div>
        ))}
      </div>

      <div className="label">Description</div>
      <p>{p.description}</p>

      <div className="label">Formats</div>
      <div className="card-notes">{p.formats.map((f) => <span key={f} className={`badge badge-${f}`}>{f}</span>)}</div>

      <div className="label"><label htmlFor="imp">My impressions</label></div>
      <textarea id="imp" aria-label="my impressions" className="search" value={impressions}
                onChange={(e) => setImpressions(e.target.value)} />
      <button onClick={() => updatePerfume(p.id, { my_impressions: impressions })}
              style={{ marginTop: 8 }}>Save impressions</button>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/views/PerfumeDetail.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/ && git commit -m "feat: perfume detail with pyramid and impressions editor"
```

---

### Task 15: Note glossary + note detail drill-down

**Files:**
- Modify: `frontend/src/views/Glossary.tsx`
- Modify: `frontend/src/views/NoteDetail.tsx`
- Create: `frontend/src/views/NoteDetail.test.tsx`

- [ ] **Step 1: Write the failing test**

`frontend/src/views/NoteDetail.test.tsx`:
```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { vi, it, expect } from "vitest";
import NoteDetail from "./NoteDetail";
import * as api from "../api";

it("shows note info and perfumes containing it", async () => {
  vi.spyOn(api, "getNote").mockResolvedValue({
    name: "bergamot", family: "Citrus", description: "Bright citrus.",
    perfumes: [{ id: 1, name: "Sauvage", house: "Dior" }],
  });
  render(<MemoryRouter initialEntries={["/note/bergamot"]}>
    <Routes><Route path="/note/:name" element={<NoteDetail />} /></Routes>
  </MemoryRouter>);
  await waitFor(() => expect(screen.getByText("bergamot")).toBeInTheDocument());
  expect(screen.getByText("Bright citrus.")).toBeInTheDocument();
  expect(screen.getByText(/Sauvage/)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/views/NoteDetail.test.tsx`
Expected: FAIL — placeholder renders "Coming soon".

- [ ] **Step 3: Write minimal implementation**

`frontend/src/views/NoteDetail.tsx`:
```tsx
import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getNote } from "../api";

type NoteData = Awaited<ReturnType<typeof getNote>>;

export default function NoteDetail() {
  const { name } = useParams();
  const [data, setData] = useState<NoteData | null>(null);
  useEffect(() => { if (name) getNote(name).then(setData); }, [name]);
  if (!data) return <div>Loading…</div>;
  return (
    <div>
      <h2>{data.name}</h2>
      <div className="card-sub">{data.family ?? "Unclassified"}</div>
      <div className="label">What it smells like</div>
      <p>{data.description || "No description yet."}</p>
      <div className="label">In your collection ({data.perfumes.length})</div>
      <div className="grid">
        {data.perfumes.map((p) => (
          <Link key={p.id} to={`/perfume/${p.id}`} className="card">
            {p.name} <span className="card-sub">· {p.house}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
```

`frontend/src/views/Glossary.tsx`:
```tsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listNotes } from "../api";

export default function Glossary() {
  const [notes, setNotes] = useState<{ id: number; name: string; family: string | null }[]>([]);
  useEffect(() => { listNotes().then(setNotes); }, []);
  return (
    <div>
      <h2>Note Glossary</h2>
      <div className="grid">
        {notes.map((n) => (
          <Link key={n.id} to={`/note/${encodeURIComponent(n.name)}`} className="card">
            <span className="card-name">{n.name}</span>
            <div className="card-sub">{n.family ?? ""}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/views/NoteDetail.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/ && git commit -m "feat: note glossary and note detail drill-down"
```

---

### Task 16: Insights view (charts)

**Files:**
- Modify: `frontend/src/views/Insights.tsx`
- Create: `frontend/src/views/Insights.test.tsx`

- [ ] **Step 1: Write the failing test**

`frontend/src/views/Insights.test.tsx`:
```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { vi, it, expect } from "vitest";
import Insights from "./Insights";
import * as api from "../api";

it("renders note frequency, families, and similar pairs", async () => {
  vi.spyOn(api, "insightNotes").mockResolvedValue([{ note: "bergamot", count: 2 }]);
  vi.spyOn(api, "insightFamilies").mockResolvedValue([{ family: "Fresh", count: 1 }]);
  vi.spyOn(api, "insightSimilar").mockResolvedValue([{ a: "Sauvage", b: "Aventus", shared: ["bergamot"], count: 1 }]);
  render(<Insights />);
  await waitFor(() => expect(screen.getByText(/Most common notes/i)).toBeInTheDocument());
  expect(screen.getByText(/Sauvage/)).toBeInTheDocument();
  expect(screen.getByText(/Aventus/)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/views/Insights.test.tsx`
Expected: FAIL — placeholder renders "Coming soon".

- [ ] **Step 3: Write minimal implementation**

`frontend/src/views/Insights.tsx`:
```tsx
import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { insightNotes, insightFamilies, insightSimilar } from "../api";

export default function Insights() {
  const [notes, setNotes] = useState<{ note: string; count: number }[]>([]);
  const [families, setFamilies] = useState<{ family: string; count: number }[]>([]);
  const [similar, setSimilar] = useState<{ a: string; b: string; shared: string[]; count: number }[]>([]);

  useEffect(() => {
    insightNotes().then(setNotes);
    insightFamilies().then(setFamilies);
    insightSimilar().then(setSimilar);
  }, []);

  return (
    <div>
      <h2>Insights</h2>

      <div className="label">Most common notes</div>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={notes.slice(0, 12)}>
          <XAxis dataKey="note" /><YAxis allowDecimals={false} /><Tooltip />
          <Bar dataKey="count" fill="#7c5cff" />
        </BarChart>
      </ResponsiveContainer>

      <div className="label">Scent families</div>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={families}>
          <XAxis dataKey="family" /><YAxis allowDecimals={false} /><Tooltip />
          <Bar dataKey="count" fill="#0ea5a0" />
        </BarChart>
      </ResponsiveContainer>

      <div className="label">Most similar pairs (shared notes)</div>
      <ul>
        {similar.slice(0, 10).map((s, i) => (
          <li key={i}>{s.a} ↔ {s.b} — {s.count} shared ({s.shared.join(", ")})</li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/views/Insights.test.tsx`
Expected: PASS.

- [ ] **Step 5: Run the full frontend suite**

Run: `npx vitest run`
Expected: ALL frontend tests PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/ && git commit -m "feat: insights view with charts and similarity"
```

---

### Task 17: End-to-end manual verification + README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README**

`README.md`:
```markdown
# Scentfolio — Perfume Tracker

Local-first app to catalogue perfumes with AI-assisted note lookup.

## Run
1. Backend: copy `backend/.env.example` to `backend/.env`, add your `ANTHROPIC_API_KEY`, then `./backend/run.sh` (serves on :8000).
2. Frontend: `cd frontend && npm run dev` (serves on :5173, proxies /api to :8000).
3. Open http://localhost:5173.

## Test
- Backend: `cd backend && source .venv/bin/activate && pytest`
- Frontend: `cd frontend && npx vitest run`
```

- [ ] **Step 2: Full manual E2E**

With both servers running:
1. Go to **Add**, type "Dior Sauvage", click **Look up** → draft appears with notes + sources.
2. Check a format, click **Save to collection** → redirected to detail with pyramid.
3. Go to **Collection**, search "bergamot" → Sauvage appears.
4. Click a note in the pyramid → **Note detail** lists Sauvage.
5. Add a second perfume, open **Insights** → charts + similarity render.

Expected: every step works against the real backend + real Claude lookup.

- [ ] **Step 3: Commit**

```bash
git add README.md && git commit -m "docs: add README with run and test instructions"
```

---

## Self-Review Notes

- **Spec coverage:** Collection + search-by-note (Tasks 6, 8, 12); AI-agent lookup with confirm/edit (Tasks 7, 9, 13); note pyramid + impressions + formats (Task 14); note glossary drill-down (Task 15); insights: note frequency, family grouping, similarity, format breakdown (Tasks 6, 8, 16); normalized notes (Task 5); error handling — lookup failure/manual entry, low-confidence flag, missing API key, duplicate check (Tasks 9, 10, 13); SQLite→Postgres portability via `make_engine` URL (Task 2). All spec sections map to tasks.
- **Deferred by spec:** ratings, ownership status, prices, auth, mobile-native — intentionally not in any task.
- **Type consistency:** `PerfumeCreate`/`NoteInput`/`Draft` names consistent across agent, schemas, repository, and API tests; frontend `Perfume`/`Note`/`Draft`/`Format`/`Tier` consistent across `types.ts`, `api.ts`, and views. Family enum identical in `schemas.py`, `agent.py`, and `Collection.tsx`.
```
