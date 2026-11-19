import { useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { getNote } from "../api";
import { useRequest } from "../lib/useRequest";

export default function NoteDetail() {
  const { name = "" } = useParams();
  const load = useCallback(
    (signal: AbortSignal) => getNote(name, signal),
    [name],
  );
  const { result } = useRequest(load);
  if (result.status === "loading") return <div role="status">Loading…</div>;
  if (result.status === "failed") return <p role="alert">{result.error}</p>;
  const data = result.data;
  return (
    <div>
      <h2>{data.name}</h2>
      <div className="card-sub">
        {data.family ?? "Unclassified"}
        {data.origin && (
          <span className={`note-origin origin-${data.origin}`}>
            {data.origin}
          </span>
        )}
      </div>
      <div className="label">What it smells like</div>
      <p>{data.description || "No description yet."}</p>
      {data.production && (
        <>
          <div className="label">How it's made</div>
          <p>{data.production}</p>
        </>
      )}
      {data.compounds && (
        <>
          <div className="label">Key compounds</div>
          <p>{data.compounds}</p>
        </>
      )}
      {data.sourcing && (
        <>
          <div className="label">Sourcing</div>
          <p>{data.sourcing}</p>
        </>
      )}
      {data.proprietary_to && (
        <>
          <div className="label">Proprietary to</div>
          <p>{data.proprietary_to}</p>
        </>
      )}
      {data.history && (
        <>
          <div className="label">History</div>
          <p>{data.history}</p>
        </>
      )}
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
