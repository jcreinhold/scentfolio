import { Link } from "react-router-dom";
import type { Perfume } from "../types";

export default function PerfumeCard({ p }: { p: Perfume }) {
  return (
    <Link to={`/perfume/${p.id}`} className="card">
      <div className="card-top">
        <span className="card-name">{p.name}</span>
        {p.formats.map((f) => <span key={f} className={`badge badge-${f}`}>{f}</span>)}
      </div>
      <div className="card-sub">{p.house}{p.year ? ` · ${p.year}` : ""}</div>
      <div className="card-notes">
        {p.notes.slice(0, 3).map((n) => <span key={n.id} className="chip">{n.name}</span>)}
      </div>
    </Link>
  );
}
