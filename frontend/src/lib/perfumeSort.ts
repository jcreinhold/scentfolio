import type { Perfume } from "../types";

export type SortKey = "name" | "house" | "year" | "family" | "notes";
export type SortDir = "asc" | "desc";

/**
 * How each sortable column reads a comparable value off a perfume.
 * Keyed by SortKey so a new column is a compile error until it's handled here.
 * Missing text sorts last (""→ we push nulls to the end explicitly in the
 * comparator); missing year sorts last regardless of direction.
 */
const ACCESSORS: Record<SortKey, (p: Perfume) => string | number> = {
  name: (p) => p.name.toLowerCase(),
  house: (p) => p.house.toLowerCase(),
  year: (p) => p.year ?? Number.NaN,
  family: (p) => p.scent_families.join(", ").toLowerCase(),
  notes: (p) => p.notes.length,
};

/** True when a value should always sink to the bottom (blank/unknown). */
function isMissing(v: string | number): boolean {
  return v === "" || (typeof v === "number" && Number.isNaN(v));
}

function compare(a: string | number, b: string | number): number {
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b));
}

/**
 * Return a new array sorted by `key`/`dir`. Never mutates `perfumes`.
 * Blank/unknown values always sort last, independent of direction, so an
 * undated or unclassified perfume never floats to the top of a descending sort.
 */
export function sortPerfumes(perfumes: Perfume[], key: SortKey, dir: SortDir): Perfume[] {
  const read = ACCESSORS[key];
  const sign = dir === "asc" ? 1 : -1;
  return [...perfumes].sort((pa, pb) => {
    const a = read(pa);
    const b = read(pb);
    const aMissing = isMissing(a);
    const bMissing = isMissing(b);
    if (aMissing || bMissing) {
      if (aMissing && bMissing) return 0;
      return aMissing ? 1 : -1; // missing always last
    }
    return sign * compare(a, b);
  });
}
