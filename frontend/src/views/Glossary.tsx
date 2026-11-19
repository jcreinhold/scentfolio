import { useState } from "react";
import { Link } from "react-router-dom";
import { listNotes, enrichMissingNotes } from "../api";
import { errorMessage, useRequest } from "../lib/useRequest";

export default function Glossary() {
  const { result, reload } = useRequest(listNotes);
  const [enriching, setEnriching] = useState(false);
  const [error, setError] = useState("");
  const notes = result.status === "ready" ? result.data : [];
  const missing = notes.filter((note) => note.needs_enrichment).length;

  async function enrich() {
    setError("");
    setEnriching(true);
    try {
      const { failed } = await enrichMissingNotes();
      if (failed)
        setError(
          `Could not enrich ${failed} ${failed === 1 ? "note" : "notes"}.`,
        );
      reload();
    } catch (e) {
      setError(errorMessage(e, "Failed to enrich notes"));
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
            {result.status === "ready" &&
              `${notes.length} notes across your collection.`}
          </div>
        </div>
        {missing > 0 && (
          <button onClick={enrich} disabled={enriching}>
            {enriching ? "Enriching…" : `Enrich notes (${missing})`}
          </button>
        )}
      </div>
      {error && <p role="alert">{error}</p>}
      {result.status === "loading" && <p role="status">Loading notes…</p>}
      {result.status === "failed" && <p role="alert">{result.error}</p>}

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
