import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getNote } from "../api";

type NoteData = Awaited<ReturnType<typeof getNote>>;

export default function NoteDetail() {
  const { name } = useParams();
  const [data, setData] = useState<NoteData | null>(null);
  useEffect(() => { if (name) getNote(name).then(setData); }, [name]);
  if (!data) return <div>Loading…</div>;
  return (
    <div>
      <h2>{data.name}</h2>
      <div className="card-sub">{data.family ?? "Unclassified"}</div>
      <div className="label">What it smells like</div>
      <p>{data.description || "No description yet."}</p>
      <div className="label">In your collection ({data.perfumes.length})</div>
      <div className="grid">
        {data.perfumes.map((p) => (
          <Link key={p.id} to={`/perfume/${p.id}`} className="card">
            {p.name} <span className="card-sub">· {p.house}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
