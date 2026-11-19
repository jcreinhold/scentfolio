import type {
  Draft,
  Perfume,
  PerfumeDraft,
  PerfumePatch,
  PerfumeSort,
  PerfumeStatus,
} from "./types";

async function request(url: string, init?: RequestInit): Promise<Response> {
  const response = await fetch(url, init);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = typeof body?.detail === "string" ? body.detail : null;
    throw new Error(detail ?? `Request failed (${response.status})`);
  }
  return response;
}

async function requestJSON<T>(url: string, init?: RequestInit): Promise<T> {
  return (await request(url, init)).json();
}

function jsonBody(method: "POST" | "PATCH", body: object): RequestInit {
  return {
    method,
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  };
}

interface PerfumeQuery {
  q?: string;
  family?: string;
  fmt?: string;
  status: PerfumeStatus;
  sort?: PerfumeSort;
  limit: number;
  offset: number;
}

export interface PerfumePage {
  perfumes: Perfume[];
  total: number;
}

export async function listPerfumes(
  query: PerfumeQuery,
  signal?: AbortSignal,
): Promise<PerfumePage> {
  const { q, family, fmt, status, sort, limit, offset } = query;
  const params = new URLSearchParams({
    status,
    limit: String(limit),
    offset: String(offset),
  });
  if (q) params.set("q", q);
  if (family) params.set("family", family);
  if (fmt) params.set("fmt", fmt);
  if (sort) {
    params.set("sort", sort.key);
    params.set("direction", sort.direction);
  }

  const response = await request(`/api/perfumes?${params}`, { signal });
  const count = response.headers.get("X-Total-Count");
  const total = Number(count);
  if (count === null || !Number.isSafeInteger(total) || total < 0) {
    throw new Error("The collection response is missing a valid total.");
  }
  return { perfumes: await response.json(), total };
}

export const getPerfume = (id: number, signal?: AbortSignal) =>
  requestJSON<Perfume>(`/api/perfumes/${id}`, { signal });

export const lookupPerfume = (name: string, signal?: AbortSignal) =>
  requestJSON<Draft>("/api/lookup", { ...jsonBody("POST", { name }), signal });

export const createPerfume = (draft: PerfumeDraft) =>
  requestJSON<Perfume>("/api/perfumes", jsonBody("POST", draft));

export const updatePerfume = (id: number, patch: PerfumePatch) =>
  requestJSON<Perfume>(`/api/perfumes/${id}`, jsonBody("PATCH", patch));

export async function deletePerfume(id: number): Promise<void> {
  await request(`/api/perfumes/${id}`, { method: "DELETE" });
}

interface MaintenanceResult {
  updated: number;
  failed?: number;
}

export const reclassifyPerfumes = () =>
  requestJSON<MaintenanceResult>("/api/perfumes/reclassify", {
    method: "POST",
  });

export const checkDuplicate = (name: string, house: string) =>
  requestJSON<{ duplicate: boolean; id: number | null }>(
    `/api/perfumes/check-duplicate?${new URLSearchParams({ name, house })}`,
  );

interface NoteEntry {
  name: string;
  family: string | null;
  description: string;
  origin: string;
  production: string;
  compounds: string;
  sourcing: string;
  proprietary_to: string;
  history: string;
}

interface NoteListItem extends NoteEntry {
  id: number;
  needs_enrichment: boolean;
}

interface NoteDetail extends NoteEntry {
  perfumes: Pick<Perfume, "id" | "name" | "house">[];
}

export const getNote = (name: string, signal?: AbortSignal) =>
  requestJSON<NoteDetail>(`/api/notes/${encodeURIComponent(name)}`, { signal });

export const listNotes = (signal?: AbortSignal) =>
  requestJSON<NoteListItem[]>("/api/notes", { signal });

export const enrichMissingNotes = () =>
  requestJSON<MaintenanceResult & { remaining: number }>(
    "/api/notes/enrich-missing",
    { method: "POST" },
  );

export interface NoteCount {
  note: string;
  count: number;
}
export interface NotesByTier {
  top: NoteCount[];
  heart: NoteCount[];
  base: NoteCount[];
}
export const insightNotes = (signal?: AbortSignal) =>
  requestJSON<NotesByTier>("/api/insights/notes", { signal });
export const insightFamilies = (signal?: AbortSignal) =>
  requestJSON<{ family: string; count: number }[]>("/api/insights/families", {
    signal,
  });

export interface SimilarPair {
  a: string;
  b: string;
  score: number;
  shared_families: string[];
  shared_top: string[];
  shared_heart: string[];
  shared_base: string[];
}
export const insightSimilar = (signal?: AbortSignal) =>
  requestJSON<SimilarPair[]>("/api/insights/similar", { signal });
