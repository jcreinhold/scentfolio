import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { getPerfume, updatePerfume, deletePerfume } from "../api";
import type { Perfume, Tier } from "../types";
import { FAMILIES } from "../lib/families";

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

  // Optimistically update the family tags; revert on failure.
  async function setFamilies(families: string[]) {
    if (!p) return;
    const prev = p;
    setP({ ...p, scent_families: families });
    try {
      await updatePerfume(p.id, { scent_families: families });
    } catch {
      setP(prev);
    }
  }

  if (!p) return <div>Loading…</div>;

  const available = FAMILIES.filter((f) => !p.scent_families.includes(f));

  return (
    <div>
      <div className="page-head">
        <div className="eyebrow">From the archive</div>
        <h2>{p.name}</h2>
        <div className="card-sub">{p.house}{p.year ? ` · ${p.year}` : ""}
          {p.perfumer ? ` · Perfumer: ${p.perfumer}` : ""}</div>
        <div className="family-tags">
          {p.scent_families.map((f) => (
            <span key={f} className="family-tag family-tag-editable">
              <span>{f}</span>
              <button type="button" className="family-tag-remove"
                      aria-label={`Remove ${f} family`}
                      onClick={() => setFamilies(p.scent_families.filter((x) => x !== f))}>×</button>
            </span>
          ))}
          {available.length > 0 && (
            <select className="family-add" aria-label="Add fragrance family" value=""
                    onChange={(e) => { if (e.target.value) setFamilies([...p.scent_families, e.target.value]); }}>
              <option value="">+ Add family</option>
              {available.map((f) => <option key={f} value={f}>{f}</option>)}
            </select>
          )}
        </div>
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
