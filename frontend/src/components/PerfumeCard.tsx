import { Link } from "react-router-dom";
import type { Perfume } from "../types";

export default function PerfumeCard({ p, onDelete }: {
  p: Perfume;
  onDelete?: (id: number) => void;
}) {
  function handleDelete(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (window.confirm(`Remove ${p.name} from your collection?`)) onDelete?.(p.id);
  }

  return (
    <Link to={`/perfume/${p.id}`} className="card">
      <div className="card-top">
        <span className="card-name">{p.name}</span>
        <div>
          {p.formats.map((f) => <span key={f} className={`badge badge-${f}`}>{f}</span>)}
          {onDelete && (
            <button className="card-remove" aria-label={`Remove ${p.name}`}
                    title="Remove from collection" onClick={handleDelete}>✕</button>
          )}
        </div>
      </div>
      <div className="card-sub">{p.house}{p.year ? ` · ${p.year}` : ""}</div>
      <div className="card-notes">
        {p.notes.slice(0, 3).map((n) => <span key={n.id} className="chip">{n.name}</span>)}
      </div>
    </Link>
  );
}
