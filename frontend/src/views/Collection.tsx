import { useEffect, useState } from "react";
import { listPerfumes, deletePerfume, updatePerfume } from "../api";
import type { Perfume } from "../types";
import PerfumeCard from "../components/PerfumeCard";

const FAMILIES = ["Citrus","Floral","Woody","Oriental","Fresh","Aromatic",
  "Fougere","Chypre","Gourmand","Leather","Other"];

export default function Collection() {
  const [perfumes, setPerfumes] = useState<Perfume[]>([]);
  const [q, setQ] = useState("");
  const [family, setFamily] = useState("");
  const [fmt, setFmt] = useState("");

  useEffect(() => {
    listPerfumes({ q: q || undefined, family: family || undefined, fmt: fmt || undefined })
      .then(setPerfumes);
  }, [q, family, fmt]);

  async function handleDelete(id: number) {
    await deletePerfume(id);
    setPerfumes((prev) => prev.filter((p) => p.id !== id));
  }

  async function handleSetFormats(id: number, formats: string[]) {
    // Optimistic update; revert on failure.
    const prev = perfumes;
    setPerfumes((cur) => cur.map((p) => (p.id === id ? { ...p, formats } : p)));
    try {
      await updatePerfume(id, { formats });
    } catch {
      setPerfumes(prev);
    }
  }

  const filtering = Boolean(q || family || fmt);

  return (
    <div>
      <div className="page-head">
        <div className="eyebrow">The Collection</div>
        <h2>Your fragrance wardrobe</h2>
        <div className="page-sub">
          {perfumes.length} {perfumes.length === 1 ? "scent" : "scents"}
          {filtering ? " matching your filters" : " on the shelf"}
        </div>
      </div>

      <input className="search" placeholder="Search names or notes…"
             value={q} onChange={(e) => setQ(e.target.value)} />
      <div className="filters">
        <select value={family} onChange={(e) => setFamily(e.target.value)}>
          <option value="">All families</option>
          {FAMILIES.map((f) => <option key={f} value={f}>{f}</option>)}
        </select>
        <select value={fmt} onChange={(e) => setFmt(e.target.value)}>
          <option value="">All formats</option>
          <option value="full">Full</option>
          <option value="travel">Travel</option>
          <option value="sample">Sample</option>
        </select>
      </div>

      {perfumes.length === 0 ? (
        <div className="empty">
          <div className="empty-title">{filtering ? "Nothing matches" : "Your shelf is empty"}</div>
          <div>{filtering ? "Try loosening a filter." : "Add your first scent to begin the archive."}</div>
        </div>
      ) : (
        <div className="grid">
          {perfumes.map((p) => (
            <PerfumeCard key={p.id} p={p} onDelete={handleDelete} onSetFormats={handleSetFormats} />
          ))}
        </div>
      )}
    </div>
  );
}
