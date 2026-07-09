import { useEffect, useState } from "react";
import { listPerfumes } from "../api";
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

  return (
    <div>
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
      <div className="grid">
        {perfumes.map((p) => <PerfumeCard key={p.id} p={p} />)}
      </div>
    </div>
  );
}
