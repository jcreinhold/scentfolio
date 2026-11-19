"""Turn fragrance records into CSV for use in spreadsheets."""

import csv
import io

from app.schemas import PerfumeOut

CSV_COLUMNS = (
    "name",
    "status",
    "house",
    "perfumer",
    "year",
    "families",
    "formats",
    "top_notes",
    "heart_notes",
    "base_notes",
    "description",
    "impressions",
)
# Some spreadsheet locales also interpret the full-width forms as formulas.
FORMULA_PREFIXES = ("=", "+", "-", "@", "\uff1d", "\uff0b", "\uff0d", "\uff20")


def _spreadsheet_cell(value: str | int) -> str | int:
    """Prefix text that a spreadsheet could read as an active cell formula."""
    if isinstance(value, str) and (
        value.startswith(("\t", "\r", "\n"))
        or value.lstrip().startswith(FORMULA_PREFIXES)
    ):
        return "'" + value
    return value


def perfume_csv(perfumes: list[PerfumeOut]) -> str:
    """Write a header and one row per perfume, with notes grouped by tier."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(CSV_COLUMNS)
    for perfume in perfumes:
        by_tier: dict[str, list[str]] = {"top": [], "heart": [], "base": []}
        for note in perfume.notes:
            if note.tier in by_tier:
                by_tier[note.tier].append(note.name)
        row = (
            perfume.name,
            perfume.status,
            perfume.house,
            perfume.perfumer or "",
            perfume.year if perfume.year is not None else "",
            "; ".join(perfume.scent_families),
            "; ".join(perfume.formats),
            "; ".join(by_tier["top"]),
            "; ".join(by_tier["heart"]),
            "; ".join(by_tier["base"]),
            perfume.description,
            perfume.my_impressions,
        )
        writer.writerow(map(_spreadsheet_cell, row))
    return buf.getvalue()
