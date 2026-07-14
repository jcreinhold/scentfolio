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
    status: Mapped[str] = mapped_column(String(20), default="collection")  # collection | saved
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
    origin: Mapped[str] = mapped_column(String(20), default="")       # natural/synthetic/both/""
    production: Mapped[str] = mapped_column(Text, default="")         # how it's harvested or made
    compounds: Mapped[str] = mapped_column(Text, default="")          # key synthetic materials
    sourcing: Mapped[str] = mapped_column(Text, default="")           # natural sourcing / regions
    proprietary_to: Mapped[str] = mapped_column(String(80), default="")  # captive molecule's house
    history: Mapped[str] = mapped_column(Text, default="")            # origin story / perfumery lore
    detail_version: Mapped[int] = mapped_column(Integer, default=0)   # enrichment schema version
    perfume_notes: Mapped[list["PerfumeNote"]] = relationship(back_populates="note")

class PerfumeNote(Base):
    __tablename__ = "perfume_notes"
    perfume_id: Mapped[int] = mapped_column(ForeignKey("perfumes.id"), primary_key=True)
    note_id: Mapped[int] = mapped_column(ForeignKey("notes.id"), primary_key=True)
    tier: Mapped[str] = mapped_column(String(10), primary_key=True)
    perfume: Mapped["Perfume"] = relationship(back_populates="perfume_notes")
    note: Mapped["Note"] = relationship(back_populates="perfume_notes")
