export type Tier = "top" | "heart" | "base";
export type Format = "full" | "travel" | "sample";

export interface Note { id: number; name: string; tier?: Tier; family?: string | null; }
export interface Perfume {
  id: number; name: string; house: string; perfumer: string | null;
  year: number | null; scent_family: string | null; description: string;
  my_impressions: string; formats: string[]; source_urls: string[]; notes: Note[];
}
export interface Draft { perfume: Omit<Perfume, "id">; confidence: "high" | "medium" | "low"; }
