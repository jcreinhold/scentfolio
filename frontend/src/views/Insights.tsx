import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { insightNotes, insightFamilies, insightSimilar } from "../api";

export default function Insights() {
  const [notes, setNotes] = useState<{ note: string; count: number }[]>([]);
  const [families, setFamilies] = useState<{ family: string; count: number }[]>([]);
  const [similar, setSimilar] = useState<{ a: string; b: string; shared: string[]; count: number }[]>([]);

  useEffect(() => {
    insightNotes().then(setNotes);
    insightFamilies().then(setFamilies);
    insightSimilar().then(setSimilar);
  }, []);

  return (
    <div>
      <h2>Insights</h2>

      <div className="label">Most common notes</div>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={notes.slice(0, 12)}>
          <XAxis dataKey="note" /><YAxis allowDecimals={false} /><Tooltip />
          <Bar dataKey="count" fill="#7c5cff" />
        </BarChart>
      </ResponsiveContainer>

      <div className="label">Scent families</div>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={families}>
          <XAxis dataKey="family" /><YAxis allowDecimals={false} /><Tooltip />
          <Bar dataKey="count" fill="#0ea5a0" />
        </BarChart>
      </ResponsiveContainer>

      <div className="label">Most similar pairs (shared notes)</div>
      <ul>
        {similar.slice(0, 10).map((s, i) => (
          <li key={i}>{s.a} ↔ {s.b} — {s.count} shared ({s.shared.join(", ")})</li>
        ))}
      </ul>
    </div>
  );
}
