import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { insightNotes, insightFamilies, insightSimilar, reclassifyPerfumes,
         type SimilarPair } from "../api";

export default function Insights() {
  const [notes, setNotes] = useState<{ note: string; count: number }[]>([]);
  const [families, setFamilies] = useState<{ family: string; count: number }[]>([]);
  const [similar, setSimilar] = useState<SimilarPair[]>([]);
  const [reclassifying, setReclassifying] = useState(false);
  const [error, setError] = useState("");

  function loadFamilies() { insightFamilies().then(setFamilies); }
  useEffect(() => {
    insightNotes().then(setNotes);
    loadFamilies();
    insightSimilar().then(setSimilar);
  }, []);

  async function reclassify() {
    setError(""); setReclassifying(true);
    try {
      await reclassifyPerfumes();
      loadFamilies();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Reclassify failed");
    } finally {
      setReclassifying(false);
    }
  }

  return (
    <div>
      <div className="collection-head">
        <div className="page-head">
          <div className="eyebrow">Patterns</div>
          <h2>Insights</h2>
          <div className="page-sub">What your collection reveals about your taste.</div>
        </div>
        <button onClick={reclassify} disabled={reclassifying}>
          {reclassifying ? "Re-classifying…" : "Re-classify families"}
        </button>
      </div>
      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <div className="label">Most common notes</div>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={notes.slice(0, 12)}>
          <XAxis dataKey="note" tick={{ fontSize: 12, fill: "#938975" }} />
          <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: "#938975" }} />
          <Tooltip cursor={{ fill: "rgba(157,74,36,0.08)" }} />
          <Bar dataKey="count" fill="#b0562b" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>

      <div className="label">Scent families</div>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={families}>
          <XAxis dataKey="family" tick={{ fontSize: 12, fill: "#938975" }} />
          <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: "#938975" }} />
          <Tooltip cursor={{ fill: "rgba(95,107,72,0.08)" }} />
          <Bar dataKey="count" fill="#5f6b48" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>

      <div className="label">Most similar pairs</div>
      <ul className="similar-list">
        {similar.slice(0, 12).map((s, i) => (
          <li key={i} className="similar-pair">
            <div className="similar-head">
              <span className="similar-names">{s.a} <span className="similar-x">↔</span> {s.b}</span>
              <span className="similar-score">{Math.round(s.score * 100)}% match</span>
            </div>
            <div className="similar-breakdown">
              {s.shared_families.length > 0 && <SharedGroup label="Families" items={s.shared_families} />}
              {s.shared_top.length > 0 && <SharedGroup label="Top" items={s.shared_top} />}
              {s.shared_heart.length > 0 && <SharedGroup label="Heart" items={s.shared_heart} />}
              {s.shared_base.length > 0 && <SharedGroup label="Base" items={s.shared_base} />}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function SharedGroup({ label, items }: { label: string; items: string[] }) {
  return (
    <span className="similar-group">
      <span className="similar-group-label">{label}</span>
      {items.map((it) => <span key={it} className="chip">{it}</span>)}
    </span>
  );
}
