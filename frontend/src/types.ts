export type Tier = "top" | "heart" | "base";
export type Format = "full" | "travel" | "sample";
export type PerfumeStatus = "collection" | "saved";
export type PerfumeSortKey =
  "name" | "house" | "year" | "family" | "perfumer" | "notes";
export type SortDirection = "asc" | "desc";

export interface PerfumeSort {
  key: PerfumeSortKey;
  direction: SortDirection;
}

export interface Note {
  id: number;
  name: string;
  tier?: Tier;
  family?: string | null;
}
export interface Perfume {
  id: number;
  name: string;
  status: PerfumeStatus;
  house: string;
  perfumer: string | null;
  year: number | null;
  scent_families: string[];
  description: string;
  my_impressions: string;
  formats: string[];
  source_urls: string[];
  notes: Note[];
}
export type PerfumeDraft = Omit<Perfume, "id" | "notes"> & {
  notes: Omit<Note, "id">[];
};

export type PerfumePatch = Partial<
  Pick<Perfume, "my_impressions" | "formats" | "scent_families" | "status">
>;

export interface Draft {
  perfume: PerfumeDraft;
  confidence: "high" | "medium" | "low";
}
