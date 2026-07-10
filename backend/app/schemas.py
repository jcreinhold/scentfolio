from typing import Literal
from pydantic import BaseModel, Field

Tier = Literal["top", "heart", "base"]
Format = Literal["full", "travel", "sample"]
Family = Literal["Citrus", "Floral", "Fruity", "Green", "Woody",
                 "Fresh", "Aromatic", "Fougere", "Chypre", "Gourmand", "Leather", "Other"]

class NoteInput(BaseModel):
    name: str
    tier: Tier
    family: str | None = None

class PerfumeCreate(BaseModel):
    name: str
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
    my_impressions: str | None = None
    formats: list[Format] | None = None
    scent_families: list[Family] | None = None

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
    scent_families: list[str]
    description: str
    my_impressions: str
    formats: list[str]
    source_urls: list[str]
    notes: list[NoteOut]
