import json
import os
import re
from typing import Literal
from pydantic import BaseModel, ValidationError
from app.schemas import PerfumeCreate
from dotenv import load_dotenv
load_dotenv()

VALID_FAMILIES = {"Citrus", "Floral", "Fruity", "Green", "Woody", "Oriental",
                  "Fresh", "Aromatic", "Fougere", "Chypre", "Gourmand", "Leather", "Other"}

class LookupError(Exception):
    pass

class Draft(BaseModel):
    perfume: PerfumeCreate
    confidence: Literal["high", "medium", "low"] = "medium"

SYSTEM_PROMPT = (
    "You are a fragrance research assistant. Given a perfume name, use web search to "
    "find its details on Fragrantica and the brand's official site. Return ONLY a JSON "
    "object (no prose) with keys: name, house, perfumer, year, scent_families, "
    "description, source_urls (list), notes (list of {name, tier one of "
    "top/heart/base, family}), confidence (high/medium/low). scent_families must be a "
    "list of 1-3 values (a perfume can span families), each one "
    f"of: {sorted(VALID_FAMILIES)}. Order them by dominance (most prominent first). "
    "If unsure of a field use null. "
    "IMPORTANT for notes: use the CANONICAL, generic note name in lowercase and "
    "singular, WITHOUT any origin or qualifier adjective, so the same note matches "
    "across different perfumes. For example use 'bergamot' (not 'Calabrian bergamot' "
    "or 'Italian bergamot'), 'rose' (not 'Bulgarian rose'), 'musk' (not 'white musk'), "
    "'pepper' (not 'Sichuan pepper'). Keep genuinely distinct notes distinct "
    "(e.g. 'pink pepper' vs 'black pepper' only if the source clearly distinguishes them)."
)

def _isolate_json(raw_text: str) -> str:
    text = raw_text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        return fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        return text[start:end + 1]
    return text

def _clean_families(value) -> list[str]:
    """Keep only valid family names, de-duplicated, order preserved.
    Accepts a list (preferred) or a single string (tolerant of older shapes)."""
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    seen: list[str] = []
    for fam in value:
        if fam in VALID_FAMILIES and fam not in seen:
            seen.append(fam)
    return seen

def extract_draft(raw_text: str) -> Draft:
    """Parse the model's JSON text into a validated Draft."""
    try:
        payload = json.loads(_isolate_json(raw_text))
    except json.JSONDecodeError as e:
        raise LookupError(f"Model did not return JSON: {raw_text[:200]}") from e
    payload["scent_families"] = _clean_families(payload.get("scent_families"))
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

VALID_ORIGINS = {"natural", "synthetic", "both"}

# Bump when enrich_notes' output shape grows so existing notes get re-enriched.
# v1: description, origin, production.  v2: + compounds, sourcing, proprietary_to.
ENRICH_VERSION = 2

NOTE_ENRICH_PROMPT = (
    "You are a fragrance expert. For each perfume note name given (a JSON array), "
    "return an object with keys: "
    "'description' (1-2 sentences on what it smells like — its olfactory character "
    "and associations); "
    "'origin' (one of 'natural', 'synthetic', or 'both' — how the note is USUALLY "
    "sourced in modern perfumery); "
    "'production' (1-2 interesting sentences on how a natural note is harvested/"
    "extracted, or how a synthetic material or accord is constructed); "
    "'compounds' (for synthetic or accord notes, the key chemical compounds or "
    "aroma materials typically used, e.g. 'galaxolide, ISO E Super'; empty string "
    "for pure naturals); "
    "'sourcing' (for natural notes, where it is typically grown/sourced and the "
    "main producing regions, e.g. 'Grasse, France; Bulgaria; Turkey'; empty string "
    "for pure synthetics); "
    "'proprietary_to' (if the material is a known captive/proprietary molecule, the "
    "fragrance house or supplier it belongs to, e.g. Akigalawood -> 'Givaudan'; "
    "empty string otherwise). "
    "Return ONLY a JSON object (no prose) mapping each note name, EXACTLY as given, "
    "to its object."
)

def _clean_str(entry: dict, key: str) -> str:
    val = entry.get(key)
    return val.strip() if isinstance(val, str) else ""

def enrich_notes(names: list[str], client=None) -> dict[str, dict]:
    """Generate {description, origin, production, compounds, sourcing,
    proprietary_to} for note names. Batched: one call for the whole `names` list.
    `client` injectable for tests. No web search."""
    if not names:
        return {}
    if client is None:
        from anthropic import Anthropic
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise LookupError("ANTHROPIC_API_KEY not set")
        client = Anthropic()
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=6000,
        system=NOTE_ENRICH_PROMPT,
        messages=[{"role": "user", "content": json.dumps(names)}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    try:
        payload = json.loads(_isolate_json(text))
    except json.JSONDecodeError as e:
        raise LookupError(f"Model did not return JSON: {text[:200]}") from e
    out: dict[str, dict] = {}
    for n in names:
        entry = payload.get(n)
        if not isinstance(entry, dict):
            continue
        origin = entry.get("origin")
        out[n] = {
            "description": _clean_str(entry, "description"),
            "origin": origin if origin in VALID_ORIGINS else "",
            "production": _clean_str(entry, "production"),
            "compounds": _clean_str(entry, "compounds"),
            "sourcing": _clean_str(entry, "sourcing"),
            "proprietary_to": _clean_str(entry, "proprietary_to"),
        }
    return out

CLASSIFY_PROMPT = (
    "You are a fragrance classification expert. Given a perfume (name, house, and "
    "its notes), research its modern scent grouping — think in terms of its main "
    "accords the way Fragrantica and Michael Edwards' fragrance wheel do, not just "
    "the literal notes. Use web search to check its accords when helpful. Return "
    "ONLY a JSON object (no prose) of the form {\"families\": [...]} with 1-3 "
    "family tags, ordered by dominance, each "
    f"one of: {sorted(VALID_FAMILIES)}. A perfume may span several families."
)

def classify_families(name: str, house: str, notes: list[str], client=None) -> list[str]:
    """Research a perfume's modern scent families and return 1-3 valid tags.
    `client` injectable for tests."""
    if client is None:
        from anthropic import Anthropic
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise LookupError("ANTHROPIC_API_KEY not set")
        client = Anthropic()
    prompt = (f"Perfume: {name}\nHouse: {house or 'unknown'}\n"
              f"Notes: {', '.join(notes) if notes else 'unknown'}\n"
              "Classify into scent families.")
    resp = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=800,
        system=CLASSIFY_PROMPT,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    try:
        payload = json.loads(_isolate_json(text))
    except json.JSONDecodeError as e:
        raise LookupError(f"Model did not return JSON: {text[:200]}") from e
    return _clean_families(payload.get("families") if isinstance(payload, dict) else payload)
