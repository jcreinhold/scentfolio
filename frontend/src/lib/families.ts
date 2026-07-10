// The scent-family vocabulary. Mirrors the backend `Family` literal
// (schemas.py) / VALID_FAMILIES (agent.py) — keep the three in sync.
export const FAMILIES = [
  "Citrus", "Floral", "Fruity", "Green", "Woody", "Fresh",
  "Aromatic", "Fougere", "Chypre", "Gourmand", "Leather", "Other",
] as const;
