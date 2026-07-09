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
