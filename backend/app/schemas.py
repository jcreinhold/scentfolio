"""Define the fragrance and glossary payloads shared by the API and storage."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Tier = Literal["top", "heart", "base"]
Format = Literal["full", "travel", "sample"]
Status = Literal["collection", "saved"]
PerfumeName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
NoteName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]
PerfumeSort = Literal["name", "house", "year", "family", "perfumer", "notes"]
SortDirection = Literal["asc", "desc"]
Family = Literal[
    "Citrus",
    "Floral",
    "Fruity",
    "Green",
    "Woody",
    "Fresh",
    "Aromatic",
    "Fougere",
    "Chypre",
    "Gourmand",
    "Leather",
    "Other",
]


class NoteInput(BaseModel):
    """A note name and the tier it occupies in a new fragrance."""

    name: NoteName
    tier: Tier
    family: str | None = None


class PerfumeCreate(BaseModel):
    """A new fragrance entry, added to the collection by default."""

    name: PerfumeName
    status: Status = "collection"
    house: str = ""
    perfumer: str | None = None
    year: int | None = None
    scent_families: list[Family] = Field(default_factory=list)
    description: str = ""
    my_impressions: str = ""
    formats: list[Format] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    notes: list[NoteInput] = Field(default_factory=list)


class PerfumeUpdate(BaseModel):
    """Editable fields for a partial update, with null fields left as they are."""

    my_impressions: str | None = None
    formats: list[Format] | None = None
    scent_families: list[Family] | None = None
    status: Status | None = None


class NoteOut(BaseModel):
    """A glossary reference with a tier when it appears on a fragrance."""

    id: int
    name: str
    tier: Tier | None = None
    family: str | None = None


class PerfumeOut(BaseModel):
    """A stored fragrance with expanded lists and note links."""

    id: int
    name: str
    status: str
    house: str
    perfumer: str | None
    year: int | None
    scent_families: list[str]
    description: str
    my_impressions: str
    formats: list[str]
    source_urls: list[str]
    notes: list[NoteOut]


class NoteContent(BaseModel):
    """Glossary content shared by list and detail responses."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    family: str | None = None
    description: str = ""
    origin: str = ""
    production: str = ""
    compounds: str = ""
    sourcing: str = ""
    proprietary_to: str = ""
    history: str = ""


class GlossaryNote(NoteContent):
    """A glossary list item with the server's enrichment status."""

    id: int
    needs_enrichment: bool


class PerfumeReference(BaseModel):
    """Identify a fragrance in a glossary cross-reference."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    house: str


class NoteDetail(NoteContent):
    """Glossary content with the fragrances that use the note."""

    perfumes: list[PerfumeReference]
