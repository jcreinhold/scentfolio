import pytest
from pydantic import ValidationError

from app.schemas import NoteInput, PerfumeCreate


def test_perfume_create_validates_format_and_family():
    p = PerfumeCreate(
        name="Aventus",
        house="Creed",
        scent_families=["Chypre", "Fruity"],
        formats=["full", "sample"],
        notes=[NoteInput(name="bergamot", tier="top")],
    )
    assert p.formats == ["full", "sample"]
    assert p.scent_families == ["Chypre", "Fruity"]


def test_invalid_format_rejected():
    with pytest.raises(ValidationError):
        PerfumeCreate(name="X", formats=["gigantic"])


def test_invalid_family_rejected():
    with pytest.raises(ValidationError):
        PerfumeCreate(name="X", scent_families=["Spacewood"])


def test_status_defaults_to_collection():
    assert PerfumeCreate(name="X").status == "collection"


def test_invalid_status_rejected():
    with pytest.raises(ValidationError):
        PerfumeCreate(name="X", status="wishlist")


def test_invalid_tier_rejected():
    with pytest.raises(ValidationError):
        NoteInput(name="rose", tier="middle")  # must be top/heart/base
