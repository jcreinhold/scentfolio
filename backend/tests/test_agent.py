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

def test_extract_draft_handles_json_code_fence():
    raw = "Here are the details I found:\n```json\n" + json.dumps({
        "name": "Aventus", "house": "Creed", "scent_family": "Chypre",
        "notes": [{"name": "bergamot", "tier": "top"}]}) + "\n```\nHope that helps!"
    draft = extract_draft(raw)
    assert draft.perfume.name == "Aventus"
    assert draft.perfume.notes[0].name == "bergamot"

def test_extract_draft_handles_preamble_without_fence():
    raw = "Sure! The perfume is: " + json.dumps({
        "name": "Sauvage", "house": "Dior", "scent_family": "Fresh", "notes": []})
    draft = extract_draft(raw)
    assert draft.perfume.name == "Sauvage"
    assert draft.perfume.house == "Dior"
