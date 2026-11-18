import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listNotes, enrichMissingNotes } from "../api";

type NoteRow = {
  id: number;
  name: string;
  family: string | null;
  description: string;
  origin: string;
  production: string;
  compounds: string;
  sourcing: string;
  proprietary_to: string;
  history: string;
};

export default function Glossary() {
  const [notes, setNotes] = useState<NoteRow[]>([]);
  const [enriching, setEnriching] = useState(false);
  const [error, setError] = useState("");

  function load() {
    listNotes().then(setNotes);
  }
  useEffect(() => {
    load();
  }, []);

  const missing = notes.filter((n) => !n.origin).length;

  async function enrich() {
    setError("");
    setEnriching(true);
    try {
      await enrichMissingNotes();
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to enrich notes");
    } finally {
      setEnriching(false);
    }
  }

  return (
    <div>
      <div className="collection-head">
        <div className="page-head">
          <div className="eyebrow">The Lexicon</div>
          <h2>Note Glossary</h2>
          <div className="page-sub">
            {notes.length} notes across your collection.
          </div>
        </div>
        {missing > 0 && (
          <button onClick={enrich} disabled={enriching}>
            {enriching ? "Enriching…" : `Enrich notes (${missing})`}
          </button>
        )}
      </div>
      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <div className="grid">
        {notes.map((n) => (
          <Link
            key={n.id}
            to={`/note/${encodeURIComponent(n.name)}`}
            className="card"
          >
            <div className="note-head">
              <span className="card-name">{n.name}</span>
              <span className="note-badges">
                {n.origin && (
                  <span className={`note-origin origin-${n.origin}`}>
                    {n.origin}
                  </span>
                )}
                {n.proprietary_to && (
                  <span
                    className="note-proprietary"
                    title={`Proprietary to ${n.proprietary_to}`}
                  >
                    {n.proprietary_to}
                  </span>
                )}
              </span>
            </div>
            {n.family && <div className="card-sub">{n.family}</div>}
            {n.description ? (
              <p className="note-desc">{n.description}</p>
            ) : (
              <p className="note-desc note-desc-empty">No description yet</p>
            )}
            {n.production && (
              <p className="note-production">
                <span className="note-production-label">How it's made</span>
                {n.production}
              </p>
            )}
            {n.compounds && (
              <p className="note-production">
                <span className="note-production-label">Key compounds</span>
                {n.compounds}
              </p>
            )}
            {n.sourcing && (
              <p className="note-production">
                <span className="note-production-label">Sourcing</span>
                {n.sourcing}
              </p>
            )}
          </Link>
        ))}
      </div>
    </div>
  );
}
