import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { lookupPerfume, createPerfume } from "../api";
import type { Draft, Format } from "../types";

const FORMATS: Format[] = ["full", "travel", "sample"];

export default function Add() {
  const [name, setName] = useState("");
  const [draft, setDraft] = useState<Draft | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const nav = useNavigate();

  async function doLookup() {
    setError(""); setLoading(true);
    try { setDraft(await lookupPerfume(name)); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }

  function patch(field: string, value: any) {
    if (!draft) return;
    setDraft({ ...draft, perfume: { ...draft.perfume, [field]: value } });
  }

  function toggleFormat(f: Format) {
    if (!draft) return;
    const has = draft.perfume.formats.includes(f);
    patch("formats", has ? draft.perfume.formats.filter((x) => x !== f)
                         : [...draft.perfume.formats, f]);
  }

  async function save() {
    if (!draft) return;
    const created = await createPerfume(draft.perfume);
    nav(`/perfume/${created.id}`);
  }

  return (
    <div>
      <h2>Add a perfume</h2>
      <div style={{ display: "flex", gap: 8 }}>
        <input className="search" placeholder="Add a perfume by name…"
               value={name} onChange={(e) => setName(e.target.value)} />
        <button onClick={doLookup} disabled={loading || !name}>
          {loading ? "Searching…" : "Look up"}
        </button>
      </div>
      {error && <p style={{ color: "crimson" }}>{error} — you can still add it manually below.</p>}

      {draft && (
        <div>
          <p className="label">{draft.confidence} confidence — verify against sources before saving</p>
          <input className="search" value={draft.perfume.name}
                 onChange={(e) => patch("name", e.target.value)} />
          <input className="search" value={draft.perfume.house}
                 onChange={(e) => patch("house", e.target.value)} placeholder="House" />
          <textarea className="search" value={draft.perfume.description}
                    onChange={(e) => patch("description", e.target.value)} />
          <div className="filters">
            {FORMATS.map((f) => (
              <label key={f}>
                <input type="checkbox" checked={draft.perfume.formats.includes(f)}
                       onChange={() => toggleFormat(f)} /> {f}
              </label>
            ))}
          </div>
          <div className="card-notes">
            {draft.perfume.notes.map((n, i) => (
              <span key={i} className="chip">
                <span>{n.name}</span>{n.tier ? ` (${n.tier})` : ""}
              </span>
            ))}
          </div>
          {draft.perfume.source_urls.map((u) => (
            <div key={u}><a href={u} target="_blank" rel="noreferrer">{u}</a></div>
          ))}
          <button onClick={save} style={{ marginTop: 12 }}>Save to collection</button>
        </div>
      )}
    </div>
  );
}
