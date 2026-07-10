import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { getPerfume, updatePerfume, deletePerfume } from "../api";
import type { Perfume, Tier } from "../types";

const TIERS: Tier[] = ["top", "heart", "base"];

export default function PerfumeDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [p, setP] = useState<Perfume | null>(null);
  const [impressions, setImpressions] = useState("");

  useEffect(() => {
    getPerfume(Number(id)).then((data) => { setP(data); setImpressions(data.my_impressions); });
  }, [id]);

  async function remove() {
    if (p && window.confirm(`Remove ${p.name} from your collection?`)) {
      await deletePerfume(p.id);
      nav("/");
    }
  }

  if (!p) return <div>Loading…</div>;

  return (
    <div>
      <div className="page-head">
        <div className="eyebrow">From the archive</div>
        <h2>{p.name}</h2>
        <div className="card-sub">{p.house}{p.year ? ` · ${p.year}` : ""}
          {p.perfumer ? ` · Perfumer: ${p.perfumer}` : ""}</div>
        {p.scent_families.length > 0 && (
          <div className="family-tags">
            {p.scent_families.map((f) => <span key={f} className="family-tag">{f}</span>)}
          </div>
        )}
      </div>

      <div className="label">Note pyramid</div>
      <div className="pyramid">
        {TIERS.map((tier) => (
          <div key={tier} className={tier}>
            <b>{tier}:</b>{" "}
            {p.notes.filter((n) => n.tier === tier).map((n, i, arr) => (
              <span key={n.id}>
                <Link to={`/note/${encodeURIComponent(n.name)}`}>{n.name}</Link>
                {i < arr.length - 1 ? ", " : ""}
              </span>
            ))}
          </div>
        ))}
      </div>

      <div className="label">Description</div>
      <p>{p.description}</p>

      <div className="label">Formats</div>
      <div className="card-notes">{p.formats.map((f) => <span key={f} className={`badge badge-${f}`}>{f}</span>)}</div>

      <div className="label"><label htmlFor="imp">My impressions</label></div>
      <textarea id="imp" aria-label="my impressions" className="search" value={impressions}
                onChange={(e) => setImpressions(e.target.value)} />
      <button onClick={() => updatePerfume(p.id, { my_impressions: impressions })}
              style={{ marginTop: 8 }}>Save impressions</button>

      <div style={{ marginTop: 32, borderTop: "1px solid #eee", paddingTop: 16 }}>
        <button className="btn-danger" onClick={remove}>Remove from collection</button>
      </div>
    </div>
  );
}
