import json
import re
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

from app.llm import LookupError, complete
from app.schemas import PerfumeCreate

load_dotenv()

VALID_FAMILIES = {
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
}


class Draft(BaseModel):
    perfume: PerfumeCreate
    confidence: Literal["high", "medium", "low"] = "medium"


SYSTEM_PROMPT = (
    "You are a fragrance research assistant. Given a perfume name, return ONLY a JSON "
    "object (no prose) with keys: name, house, perfumer, year, scent_families, "
    "description, notes (list of {name, tier one of "
    "top/heart/base, family}), confidence (high/medium/low). scent_families must be a "
    "list of 1-3 values (a perfume can span families), each one "
    f"of: {sorted(VALID_FAMILIES)}. Order them by dominance (most prominent first). "
    "Omit unknown details, keeping the supplied perfume name. "
    "IMPORTANT for notes: use the CANONICAL, generic note name in lowercase and "
    "singular, WITHOUT any origin or qualifier adjective, so the same note matches "
    "across different perfumes. For example use 'bergamot' (not 'Calabrian bergamot' "
    "or 'Italian bergamot'), 'rose' (not 'Bulgarian rose'), 'musk' (not 'white musk'), "
    "'pepper' (not 'Sichuan pepper'). Keep genuinely distinct notes distinct "
    "(e.g. 'pink pepper' vs 'black pepper' only if the source clearly "
    "distinguishes them)."
)
LOOKUP_SEARCH = (
    "Use web search to find details on Fragrantica and the brand's official site."
)


def _isolate_json(raw_text: str) -> str:
    text = raw_text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        return fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        return text[start : end + 1]
    return text


def _parse_json(raw_text: str):
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        try:
            return json.loads(_isolate_json(raw_text))
        except json.JSONDecodeError as exc:
            raise LookupError("Model did not return JSON") from exc


def _clean_families(value) -> list[str]:
    """Keep only valid family names, de-duplicated, order preserved.
    Accepts a list (preferred) or a single string (tolerant of older shapes)."""
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    seen: list[str] = []
    for fam in value:
        if isinstance(fam, str) and fam in VALID_FAMILIES and fam not in seen:
            seen.append(fam)
    return seen


def extract_draft(raw_text: str, *, source_urls: list[str] | None = None) -> Draft:
    """Parse the model's JSON text into a validated Draft."""
    payload = _parse_json(raw_text)
    if not isinstance(payload, dict):
        raise LookupError("Model did not return a perfume object")

    payload["scent_families"] = _clean_families(payload.get("scent_families"))
    notes = payload.get("notes")
    payload["notes"] = [
        note
        for note in (notes if isinstance(notes, list) else [])
        if isinstance(note, dict) and note.get("tier") in ("top", "heart", "base")
    ]
    confidence = payload.pop("confidence", "medium")
    if source_urls is not None:
        payload["source_urls"] = source_urls
        if not source_urls:
            confidence = "low"
    try:
        return Draft(perfume=PerfumeCreate(**payload), confidence=confidence)
    except ValidationError as exc:
        raise LookupError("Model returned invalid perfume data") from exc


def lookup(name: str) -> Draft:
    """Look up a perfume with the configured model."""
    text, sources = complete(
        SYSTEM_PROMPT,
        f"Look up the perfume: {name}",
        max_tokens=1500,
        task="lookup",
        search=LOOKUP_SEARCH,
    )
    return extract_draft(text, source_urls=sources)


VALID_ORIGINS = {"natural", "synthetic", "both"}

# Bump when enrich_notes' output shape grows so existing notes get re-enriched.
# v1: description, origin, production.  v2: + compounds, sourcing, proprietary_to.
# v3: richer educational sourcing/compounds + history.
ENRICH_VERSION = 3

NOTE_ENRICH_PROMPT = (
    "You are a fragrance expert writing for an enthusiast who wants to LEARN about "
    "perfumery. For each perfume note name given (a JSON array), return an object "
    "with keys: "
    "'description' (1-2 sentences on what it smells like — its olfactory character "
    "and associations); "
    "'origin' (one of 'natural', 'synthetic', or 'both' — how the note is USUALLY "
    "sourced in modern perfumery); "
    "'production' (1-2 interesting sentences on how a natural note is harvested/"
    "extracted, or how a synthetic material or accord is constructed); "
    "'compounds' (for synthetic or accord notes, break down the KEY aroma-chemicals "
    "and what EACH one smells like — e.g. for aldehydes: C-10 waxy orange peel, "
    "C-11 green, C-12 soapy/lilac; 2-4 sentences; empty string for pure naturals); "
    "'sourcing' (for natural notes, 2-4 sentences on how the scent differs by origin "
    "and terroir — e.g. Bulgarian vs Turkish vs Grasse rose — where it is most "
    "prized, and relevant cultural background; empty string for pure synthetics); "
    "'proprietary_to' (if the material is a known captive/proprietary molecule, the "
    "fragrance house or supplier it belongs to, e.g. Akigalawood -> 'Givaudan'; "
    "empty string otherwise); "
    "'history' (2-3 sentences: the material's origin or discovery story, a notable "
    "moment in perfumery — e.g. aldehydes in Chanel No.5 — and its cultural "
    "significance). "
    "Return ONLY a JSON object (no prose) mapping each note name, EXACTLY as given, "
    "to its object."
)


def _clean_str(entry: dict, key: str) -> str:
    val = entry.get(key)
    return val.strip() if isinstance(val, str) else ""


def enrich_notes(names: list[str]) -> dict[str, dict]:
    """Generate glossary entries for the whole batch in a single call."""
    if not names:
        return {}
    text, _ = complete(
        NOTE_ENRICH_PROMPT,
        json.dumps(names),
        max_tokens=8000,
        task="enrich",
    )
    payload = _parse_json(text)
    if not isinstance(payload, dict):
        raise LookupError("Model did not return a note object")
    out: dict[str, dict] = {}
    for n in names:
        entry = payload.get(n)
        if not isinstance(entry, dict):
            continue
        origin = _clean_str(entry, "origin")
        out[n] = {
            "description": _clean_str(entry, "description"),
            "origin": origin if origin in VALID_ORIGINS else "",
            "production": _clean_str(entry, "production"),
            "compounds": _clean_str(entry, "compounds"),
            "sourcing": _clean_str(entry, "sourcing"),
            "proprietary_to": _clean_str(entry, "proprietary_to"),
            "history": _clean_str(entry, "history"),
        }
    return out


CLASSIFY_PROMPT = (
    "You are a fragrance classification expert. Given a perfume (name, house, and "
    "its notes), research its modern scent grouping — think in terms of its main "
    "accords the way Fragrantica and Michael Edwards' fragrance wheel do, not just "
    "the literal notes. Return "
    'ONLY a JSON object (no prose) of the form {"families": [...]} with 1-3 '
    "family tags, ordered by dominance, each "
    f"one of: {sorted(VALID_FAMILIES)}. A perfume may span several families."
)


def classify_families(name: str, house: str, notes: list[str]) -> list[str]:
    """Classify a perfume into its most prominent scent families."""
    prompt = (
        f"Perfume: {name}\nHouse: {house or 'unknown'}\n"
        f"Notes: {', '.join(notes) if notes else 'unknown'}\n"
        "Classify into scent families."
    )
    text, _ = complete(
        CLASSIFY_PROMPT,
        prompt,
        max_tokens=800,
        task="classify",
        search="Use web search to check its accords when helpful.",
    )
    payload = _parse_json(text)
    return _clean_families(
        payload.get("families") if isinstance(payload, dict) else payload
    )
