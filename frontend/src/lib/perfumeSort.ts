import type { Perfume } from "../types";

export type SortKey =
  "name" | "house" | "perfumer" | "year" | "family" | "notes";
export type SortDir = "asc" | "desc";

/** Whole-collection context some sorts need (e.g. per-perfumer counts). */
interface SortContext {
  /** lowercased perfumer name → how many perfumes in the set share it */
  perfumerCounts: Map<string, number>;
}

function countPerfumers(perfumes: Perfume[]): Map<string, number> {
  const counts = new Map<string, number>();
  for (const p of perfumes) {
    if (!p.perfumer) continue;
    const key = p.perfumer.toLowerCase();
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return counts;
}

/**
 * How each sortable column reads a comparable value off a perfume.
 * Keyed by SortKey so a new column is a compile error until it's handled here.
 * The `perfumer` sort is by collection frequency — how many perfumes share that
 * perfumer — so the perfumers you own most of lead the list.
 */
const ACCESSORS: Record<
  SortKey,
  (p: Perfume, ctx: SortContext) => string | number
> = {
  name: (p) => p.name.toLowerCase(),
  house: (p) => p.house.toLowerCase(),
  year: (p) => p.year ?? Number.NaN,
  family: (p) => p.scent_families.join(", ").toLowerCase(),
  notes: (p) => p.notes.length,
  perfumer: (p, ctx) =>
    p.perfumer
      ? (ctx.perfumerCounts.get(p.perfumer.toLowerCase()) ?? 0)
      : Number.NaN,
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
 * When sorting by `perfumer` (a count), ties are broken by perfumer name so all
 * perfumes from the same perfumer stay grouped together regardless of direction.
 */
export function sortPerfumes(
  perfumes: Perfume[],
  key: SortKey,
  dir: SortDir,
): Perfume[] {
  const ctx: SortContext = { perfumerCounts: countPerfumers(perfumes) };
  const read = ACCESSORS[key];
  const sign = dir === "asc" ? 1 : -1;
  return [...perfumes].sort((pa, pb) => {
    const a = read(pa, ctx);
    const b = read(pb, ctx);
    const aMissing = isMissing(a);
    const bMissing = isMissing(b);
    if (aMissing || bMissing) {
      if (aMissing && bMissing) return 0;
      return aMissing ? 1 : -1; // missing always last
    }
    const primary = sign * compare(a, b);
    if (primary !== 0) return primary;
    if (key === "perfumer") {
      // group same perfumer together (direction-independent)
      return compare(
        (pa.perfumer ?? "").toLowerCase(),
        (pb.perfumer ?? "").toLowerCase(),
      );
    }
    return 0;
  });
}
