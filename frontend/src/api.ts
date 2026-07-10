import type { Perfume, Draft } from "./types";

/**
 * Run `fn` over `items` with at most `limit` calls in flight at once.
 * Results are returned in input order. Each result is a settled outcome so one
 * rejection never sinks the batch: `{ ok: true, value }` or `{ ok: false, error }`.
 */
export type Settled<T> = { ok: true; value: T } | { ok: false; error: unknown };

export async function mapPool<I, O>(
  items: I[], limit: number, fn: (item: I, index: number) => Promise<O>,
  onSettle?: (index: number, result: Settled<O>) => void,
): Promise<Settled<O>[]> {
  const results = new Array<Settled<O>>(items.length);
  let next = 0;
  const worker = async () => {
    while (next < items.length) {
      const i = next++;
      let settled: Settled<O>;
      try {
        settled = { ok: true, value: await fn(items[i], i) };
      } catch (error) {
        settled = { ok: false, error };
      }
      results[i] = settled;
      onSettle?.(i, settled);
    }
  };
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker));
  return results;
}

async function getJSON<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`GET ${url} failed: ${r.status}`);
  return r.json();
}

export async function listPerfumes(
  filters: { q?: string; family?: string; fmt?: string } = {}
): Promise<Perfume[]> {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.family) params.set("family", filters.family);
  if (filters.fmt) params.set("fmt", filters.fmt);
  const qs = params.toString();
  return getJSON(`/api/perfumes${qs ? `?${qs}` : ""}`);
}

export const getPerfume = (id: number) => getJSON<Perfume>(`/api/perfumes/${id}`);

export async function lookupPerfume(name: string): Promise<Draft> {
  const r = await fetch("/api/lookup", {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!r.ok) throw new Error((await r.json()).detail ?? "Lookup failed");
  return r.json();
}

export async function createPerfume(draft: Draft["perfume"]): Promise<Perfume> {
  const r = await fetch("/api/perfumes", {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify(draft),
  });
  if (!r.ok) throw new Error("Create failed");
  return r.json();
}

export async function updatePerfume(
  id: number, patch: { my_impressions?: string; formats?: string[] }
): Promise<Perfume> {
  const r = await fetch(`/api/perfumes/${id}`, {
    method: "PATCH", headers: { "content-type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!r.ok) throw new Error("Update failed");
  return r.json();
}

export async function deletePerfume(id: number): Promise<void> {
  const r = await fetch(`/api/perfumes/${id}`, { method: "DELETE" });
  if (!r.ok) throw new Error("Delete failed");
}

export async function reclassifyPerfumes(): Promise<{ updated: number }> {
  const r = await fetch("/api/perfumes/reclassify", { method: "POST" });
  if (!r.ok) throw new Error("Reclassify failed");
  return r.json();
}

export const checkDuplicate = (name: string, house: string) =>
  getJSON<{ duplicate: boolean; id: number | null }>(
    `/api/perfumes/check-duplicate?name=${encodeURIComponent(name)}&house=${encodeURIComponent(house)}`);

export const getNote = (name: string) =>
  getJSON<{ name: string; family: string | null; description: string;
            origin: string; production: string; compounds: string;
            sourcing: string; proprietary_to: string;
            perfumes: { id: number; name: string; house: string }[] }>(
    `/api/notes/${encodeURIComponent(name)}`);
export const listNotes = () =>
  getJSON<{ id: number; name: string; family: string | null;
            description: string; origin: string; production: string;
            compounds: string; sourcing: string; proprietary_to: string }[]>(`/api/notes`);

export async function enrichMissingNotes(): Promise<{ updated: number }> {
  const r = await fetch("/api/notes/enrich-missing", { method: "POST" });
  if (!r.ok) throw new Error("Failed to enrich notes");
  return r.json();
}
export const insightNotes = () => getJSON<{ note: string; count: number }[]>(`/api/insights/notes`);
export const insightFamilies = () => getJSON<{ family: string; count: number }[]>(`/api/insights/families`);
export const insightSimilar = () => getJSON<{ a: string; b: string; shared: string[]; count: number }[]>(`/api/insights/similar`);
