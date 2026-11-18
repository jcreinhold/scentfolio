import json
import pytest
from app.agent import extract_draft, enrich_notes, classify_families, LookupError


class _Block:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _Resp:
    def __init__(self, text):
        self.content = [_Block(text)]


class _FakeClient:
    """Mimics anthropic client: .messages.create(...) -> object with .content."""

    def __init__(self, reply_text):
        self._reply = reply_text
        self.calls = []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _Resp(self._reply)


def _fake_response(payload: dict):
    # Mimics the shape agent.extract_draft expects: a JSON string of the draft.
    return json.dumps(payload)


def test_extract_draft_parses_valid_payload():
    raw = _fake_response(
        {
            "name": "Aventus",
            "house": "Creed",
            "perfumer": "Olivier Creed",
            "year": 2010,
            "scent_families": ["Chypre", "Fruity"],
            "description": "Fruity smoky signature scent.",
            "source_urls": ["https://www.fragrantica.com/perfume/x"],
            "notes": [
                {"name": "pineapple", "tier": "top"},
                {"name": "birch", "tier": "heart", "family": "Woody"},
            ],
            "confidence": "high",
        }
    )
    draft = extract_draft(raw)
    assert draft.perfume.name == "Aventus"
    assert draft.confidence == "high"
    assert draft.perfume.notes[0].name == "pineapple"
    assert draft.perfume.scent_families == ["Chypre", "Fruity"]


def test_extract_draft_drops_invalid_families_and_dedupes():
    raw = _fake_response(
        {
            "name": "X",
            "scent_families": ["Gourmand", "Spacewood", "Gourmand", "Green"],
            "notes": [],
        }
    )
    draft = extract_draft(raw)
    assert draft.perfume.scent_families == ["Gourmand", "Green"]


def test_extract_draft_missing_families_defaults_empty():
    draft = extract_draft(_fake_response({"name": "X", "notes": []}))
    assert draft.perfume.scent_families == []


def test_extract_draft_rejects_non_json():
    with pytest.raises(LookupError):
        extract_draft("I could not find this perfume.")


def test_extract_draft_handles_json_code_fence():
    raw = (
        "Here are the details I found:\n```json\n"
        + json.dumps(
            {
                "name": "Aventus",
                "house": "Creed",
                "scent_families": ["Chypre"],
                "notes": [{"name": "bergamot", "tier": "top"}],
            }
        )
        + "\n```\nHope that helps!"
    )
    draft = extract_draft(raw)
    assert draft.perfume.name == "Aventus"
    assert draft.perfume.notes[0].name == "bergamot"


def test_extract_draft_handles_preamble_without_fence():
    raw = "Sure! The perfume is: " + json.dumps(
        {"name": "Sauvage", "house": "Dior", "scent_families": ["Fresh"], "notes": []}
    )
    draft = extract_draft(raw)
    assert draft.perfume.name == "Sauvage"
    assert draft.perfume.house == "Dior"


def test_enrich_notes_returns_full_object_for_requested_names():
    client = _FakeClient(
        json.dumps(
            {
                "bergamot": {
                    "description": "Bright citrus.",
                    "origin": "natural",
                    "production": "Cold-pressed from the peel.",
                    "sourcing": "Calabria, Italy",
                    "compounds": "",
                    "proprietary_to": "",
                },
                "akigalawood": {
                    "description": "Woody peppery.",
                    "origin": "synthetic",
                    "production": "Made by biotech fractionation of patchouli.",
                    "compounds": "patchouli-derived fraction",
                    "sourcing": "",
                    "proprietary_to": "Givaudan",
                    "history": "Introduced by Givaudan in 2015.",
                },
                "extra": {"description": "x", "origin": "natural", "production": "y"},
            }
        )
    )
    out = enrich_notes(["bergamot", "akigalawood"], client=client)
    assert set(out) == {"bergamot", "akigalawood"}  # only requested names kept
    assert out["bergamot"]["sourcing"] == "Calabria, Italy"
    assert out["bergamot"]["compounds"] == ""
    assert out["akigalawood"]["proprietary_to"] == "Givaudan"
    assert out["akigalawood"]["compounds"] == "patchouli-derived fraction"
    assert out["akigalawood"]["history"] == "Introduced by Givaudan in 2015."


def test_enrich_notes_empty_input_makes_no_call():
    client = _FakeClient("{}")
    assert enrich_notes([], client=client) == {}
    assert client.calls == []


def test_enrich_notes_coerces_invalid_origin_to_blank():
    client = _FakeClient(
        json.dumps(
            {
                "rose": {
                    "description": "Floral.",
                    "origin": "alien",
                    "production": "steam-distilled",
                }
            }
        )
    )
    out = enrich_notes(["rose"], client=client)
    assert out["rose"]["origin"] == ""  # invalid origin dropped
    assert out["rose"]["production"] == "steam-distilled"


def test_enrich_notes_handles_code_fence():
    client = _FakeClient(
        "```json\n"
        + json.dumps(
            {
                "rose": {
                    "description": "Lush.",
                    "origin": "natural",
                    "production": "distilled",
                }
            }
        )
        + "\n```"
    )
    assert enrich_notes(["rose"], client=client)["rose"]["origin"] == "natural"


def test_enrich_notes_rejects_non_json():
    with pytest.raises(LookupError):
        enrich_notes(["rose"], client=_FakeClient("I cannot help with that."))


def test_classify_families_returns_valid_tags():
    client = _FakeClient(json.dumps({"families": ["Gourmand", "Woody"]}))
    out = classify_families("Milk", "Snif", ["milk", "sandalwood"], client=client)
    assert out == ["Gourmand", "Woody"]


def test_classify_families_drops_invalid_and_dedupes():
    client = _FakeClient(
        json.dumps({"families": ["Floral", "Nonsense", "Floral", "Fruity"]})
    )
    assert classify_families("Pony Boy", "Snif", [], client=client) == [
        "Floral",
        "Fruity",
    ]


def test_classify_families_handles_preamble_and_fence():
    client = _FakeClient(
        "Based on its accords:\n```json\n"
        + json.dumps({"families": ["Green", "Gourmand"]})
        + "\n```"
    )
    assert classify_families("Dandelion Butter", "Snif", [], client=client) == [
        "Green",
        "Gourmand",
    ]


def test_classify_families_rejects_non_json():
    with pytest.raises(LookupError):
        classify_families("X", "Y", [], client=_FakeClient("no idea"))
