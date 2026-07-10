import json
import os
import re
from typing import Literal
from pydantic import BaseModel, ValidationError
from app.schemas import PerfumeCreate
from dotenv import load_dotenv
load_dotenv()

VALID_FAMILIES = {"Citrus", "Floral", "Woody", "Oriental", "Fresh", "Aromatic",
                  "Fougere", "Chypre", "Gourmand", "Leather", "Other"}

class LookupError(Exception):
    pass

class Draft(BaseModel):
    perfume: PerfumeCreate
    confidence: Literal["high", "medium", "low"] = "medium"

SYSTEM_PROMPT = (
    "You are a fragrance research assistant. Given a perfume name, use web search to "
    "find its details on Fragrantica and the brand's official site. Return ONLY a JSON "
    "object (no prose) with keys: name, house, perfumer, year, scent_family, "
    "description, source_urls (list), notes (list of {name, tier one of "
    "top/heart/base, family}), confidence (high/medium/low). scent_family must be one "
    f"of: {sorted(VALID_FAMILIES)}. If unsure of a field use null. "
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

def extract_draft(raw_text: str) -> Draft:
    """Parse the model's JSON text into a validated Draft."""
    try:
        payload = json.loads(_isolate_json(raw_text))
    except json.JSONDecodeError as e:
        raise LookupError(f"Model did not return JSON: {raw_text[:200]}") from e
    if payload.get("scent_family") not in VALID_FAMILIES:
        payload["scent_family"] = "Other" if payload.get("scent_family") else None
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

NOTE_DESC_PROMPT = (
    "You are a fragrance expert. For each perfume note name given (a JSON array), "
    "write a concise 1-2 sentence description of what it smells like — its "
    "olfactory character and common associations. Return ONLY a JSON object (no "
    "prose) mapping each note name, EXACTLY as given, to its description string."
)

def describe_notes(names: list[str], client=None) -> dict[str, str]:
    """Generate short scent descriptions for note names. Batched: one call for
    the whole `names` list. `client` injectable for tests. No web search needed."""
    if not names:
        return {}
    if client is None:
        from anthropic import Anthropic
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise LookupError("ANTHROPIC_API_KEY not set")
        client = Anthropic()
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        system=NOTE_DESC_PROMPT,
        messages=[{"role": "user", "content": json.dumps(names)}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    try:
        payload = json.loads(_isolate_json(text))
    except json.JSONDecodeError as e:
        raise LookupError(f"Model did not return JSON: {text[:200]}") from e
    # Keep only requested names with non-empty string descriptions.
    return {n: payload[n] for n in names
            if isinstance(payload.get(n), str) and payload[n].strip()}
