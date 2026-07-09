import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listNotes } from "../api";

export default function Glossary() {
  const [notes, setNotes] = useState<{ id: number; name: string; family: string | null }[]>([]);
  useEffect(() => { listNotes().then(setNotes); }, []);
  return (
    <div>
      <h2>Note Glossary</h2>
      <div className="grid">
        {notes.map((n) => (
          <Link key={n.id} to={`/note/${encodeURIComponent(n.name)}`} className="card">
            <span className="card-name">{n.name}</span>
            <div className="card-sub">{n.family ?? ""}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
