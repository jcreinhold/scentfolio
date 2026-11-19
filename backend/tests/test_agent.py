import json

import pytest

from app.agent import (
    LookupError,
    classify_families,
    enrich_notes,
    extract_draft,
    lookup,
)


def _reply(monkeypatch, text):
    monkeypatch.setattr("app.agent.complete", lambda *_args, **_options: (text, []))


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


@pytest.mark.parametrize("raw", ["```json\nnull\n```", '[{"name": "Aventus"}]'])
def test_extract_draft_rejects_non_object_json(raw):
    with pytest.raises(LookupError):
        extract_draft(raw)


def test_extract_draft_drops_malformed_families_and_notes():
    draft = extract_draft(
        _fake_response(
            {
                "name": "Aventus",
                "scent_families": [{"name": "Woody"}, "Fruity"],
                "notes": [None, {"name": "pineapple", "tier": "top"}],
            }
        )
    )
    assert draft.perfume.scent_families == ["Fruity"]
    assert [note.name for note in draft.perfume.notes] == ["pineapple"]


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


def test_lookup_without_search_clears_sources_and_lowers_confidence(monkeypatch):
    def complete(_system, _prompt, *, task, search=None, **_options):
        assert task == "lookup"
        assert search
        return (
            _fake_response(
                {
                    "name": "Aventus",
                    "source_urls": ["https://example.test/aventus"],
                    "confidence": "high",
                }
            ),
            [],
        )

    monkeypatch.setattr("app.agent.complete", complete)
    draft = lookup("Aventus")
    assert draft.perfume.name == "Aventus"
    assert draft.perfume.source_urls == []
    assert draft.confidence == "low"


def test_lookup_prefers_provider_citations_to_model_generated_urls(monkeypatch):
    source = "https://brand.example/perfume"

    def complete(*_args, **_options):
        return (
            _fake_response(
                {
                    "name": "Aventus",
                    "source_urls": ["https://example.test/unverified"],
                    "confidence": "high",
                }
            ),
            [source],
        )

    monkeypatch.setattr("app.agent.complete", complete)
    draft = lookup("Aventus")
    assert draft.perfume.source_urls == [source]
    assert draft.confidence == "high"


def test_enrich_notes_returns_full_object_for_requested_names(monkeypatch):
    _reply(
        monkeypatch,
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
        ),
    )
    out = enrich_notes(["bergamot", "akigalawood"])
    assert set(out) == {"bergamot", "akigalawood"}  # only requested names kept
    assert out["bergamot"]["sourcing"] == "Calabria, Italy"
    assert out["bergamot"]["compounds"] == ""
    assert out["akigalawood"]["proprietary_to"] == "Givaudan"
    assert out["akigalawood"]["compounds"] == "patchouli-derived fraction"
    assert out["akigalawood"]["history"] == "Introduced by Givaudan in 2015."


def test_enrich_notes_empty_input_makes_no_call(monkeypatch):
    def complete(*_args, **_options):
        pytest.fail("An empty batch should skip the model call")

    monkeypatch.setattr("app.agent.complete", complete)
    assert enrich_notes([]) == {}


def test_enrich_notes_omits_search_and_cleans_non_string_origin(monkeypatch):
    def complete(_system, prompt, *, task, search=None, **_options):
        assert task == "enrich"
        assert search is None
        assert json.loads(prompt) == ["rose"]
        return (
            _fake_response({"rose": {"description": "Floral.", "origin": ["natural"]}}),
            [],
        )

    monkeypatch.setattr("app.agent.complete", complete)
    note = enrich_notes(["rose"])["rose"]
    assert note["description"] == "Floral."
    assert note["origin"] == ""


def test_enrich_notes_coerces_invalid_origin_to_blank(monkeypatch):
    _reply(
        monkeypatch,
        json.dumps(
            {
                "rose": {
                    "description": "Floral.",
                    "origin": "alien",
                    "production": "steam-distilled",
                }
            }
        ),
    )
    out = enrich_notes(["rose"])
    assert out["rose"]["origin"] == ""  # invalid origin dropped
    assert out["rose"]["production"] == "steam-distilled"


def test_enrich_notes_handles_code_fence(monkeypatch):
    _reply(
        monkeypatch,
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
        + "\n```",
    )
    assert enrich_notes(["rose"])["rose"]["origin"] == "natural"


def test_enrich_notes_rejects_non_json(monkeypatch):
    _reply(monkeypatch, "I cannot help with that.")
    with pytest.raises(LookupError):
        enrich_notes(["rose"])


def test_classify_families_returns_valid_tags(monkeypatch):
    _reply(monkeypatch, json.dumps({"families": ["Gourmand", "Woody"]}))
    out = classify_families("Milk", "Snif", ["milk", "sandalwood"])
    assert out == ["Gourmand", "Woody"]


def test_classify_families_requests_search(monkeypatch):
    def complete(_system, _prompt, *, task, search=None, **_options):
        assert task == "classify"
        assert search
        return _fake_response({"families": ["Gourmand"]}), []

    monkeypatch.setattr("app.agent.complete", complete)
    assert classify_families("Milk", "Snif", []) == ["Gourmand"]


def test_classify_families_drops_invalid_and_dedupes(monkeypatch):
    _reply(
        monkeypatch,
        json.dumps({"families": ["Floral", "Nonsense", "Floral", "Fruity"]}),
    )
    assert classify_families("Pony Boy", "Snif", []) == [
        "Floral",
        "Fruity",
    ]


def test_classify_families_handles_preamble_and_fence(monkeypatch):
    _reply(
        monkeypatch,
        "Based on its accords:\n```json\n"
        + json.dumps({"families": ["Green", "Gourmand"]})
        + "\n```",
    )
    assert classify_families("Dandelion Butter", "Snif", []) == [
        "Green",
        "Gourmand",
    ]


def test_classify_families_rejects_non_json(monkeypatch):
    _reply(monkeypatch, "no idea")
    with pytest.raises(LookupError):
        classify_families("X", "Y", [])
