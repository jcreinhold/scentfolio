import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listNotes, describeMissingNotes } from "../api";

type NoteRow = { id: number; name: string; family: string | null; description: string };

export default function Glossary() {
  const [notes, setNotes] = useState<NoteRow[]>([]);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  function load() { listNotes().then(setNotes); }
  useEffect(() => { load(); }, []);

  const missing = notes.filter((n) => !n.description).length;

  async function generate() {
    setError(""); setGenerating(true);
    try {
      await describeMissingNotes();
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate descriptions");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div>
      <div className="collection-head">
        <div className="page-head">
          <div className="eyebrow">The Lexicon</div>
          <h2>Note Glossary</h2>
          <div className="page-sub">{notes.length} notes across your collection.</div>
        </div>
        {missing > 0 && (
          <button onClick={generate} disabled={generating}>
            {generating ? "Generating…" : `Generate descriptions (${missing})`}
          </button>
        )}
      </div>
      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <div className="grid">
        {notes.map((n) => (
          <Link key={n.id} to={`/note/${encodeURIComponent(n.name)}`} className="card">
            <span className="card-name">{n.name}</span>
            {n.family && <div className="card-sub">{n.family}</div>}
            {n.description
              ? <p className="note-desc">{n.description}</p>
              : <p className="note-desc note-desc-empty">No description yet</p>}
          </Link>
        ))}
      </div>
    </div>
  );
}
