import { Link } from "react-router-dom";
import type { Perfume, Tier, Format } from "../types";

const TIERS: { tier: Tier; label: string }[] = [
  { tier: "top", label: "Top" },
  { tier: "heart", label: "Middle" },
  { tier: "base", label: "Base" },
];
const MAX_PER_TIER = 3;
const FORMATS: { fmt: Format; label: string }[] = [
  { fmt: "full", label: "Full" },
  { fmt: "travel", label: "Travel" },
  { fmt: "sample", label: "Sample" },
];

export default function PerfumeCard({ p, onDelete, onSetFormats }: {
  p: Perfume;
  onDelete?: (id: number) => void;
  onSetFormats?: (id: number, formats: string[]) => void;
}) {
  function handleDelete(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (window.confirm(`Remove ${p.name} from your collection?`)) onDelete?.(p.id);
  }

  function toggleFormat(e: React.MouseEvent, fmt: Format) {
    e.preventDefault();
    e.stopPropagation();
    const has = p.formats.includes(fmt);
    const next = has ? p.formats.filter((x) => x !== fmt) : [...p.formats, fmt];
    onSetFormats?.(p.id, next);
  }

  return (
    <Link to={`/perfume/${p.id}`} className="card">
      <div className="card-top">
        <span className="card-name">{p.name}</span>
        {onDelete && (
          <button className="card-remove" aria-label={`Remove ${p.name}`}
                  title="Remove from collection" onClick={handleDelete}>✕</button>
        )}
      </div>
      <div className="card-sub">{p.house}{p.year ? ` · ${p.year}` : ""}</div>
      {p.perfumer && <div className="card-perfumer">By {p.perfumer}</div>}
      {p.scent_families.length > 0 && (
        <div className="family-tags">
          {p.scent_families.map((f) => <span key={f} className="family-tag">{f}</span>)}
        </div>
      )}

      <div className="card-pyramid">
        {TIERS.map(({ tier, label }) => {
          const notes = p.notes.filter((n) => n.tier === tier);
          if (notes.length === 0) return null;
          const extra = notes.length - MAX_PER_TIER;
          return (
            <div key={tier} className="card-tier">
              <span className={`tier-label tier-${tier}`}>{label}</span>
              <div className="card-notes">
                {notes.slice(0, MAX_PER_TIER).map((n) => (
                  <span key={n.id} className="chip">{n.name}</span>
                ))}
                {extra > 0 && <span className="chip chip-more">+{extra}</span>}
              </div>
            </div>
          );
        })}
      </div>

      {onSetFormats && (
        <div className="card-formats">
          <span className="fmt-label">Size</span>
          {FORMATS.map(({ fmt, label }) => {
            const on = p.formats.includes(fmt);
            return (
              <button key={fmt} type="button"
                      className={`fmt-toggle${on ? " on" : ""}`}
                      aria-pressed={on}
                      aria-label={`${on ? "Remove" : "Add"} ${label} size for ${p.name}`}
                      onClick={(e) => toggleFormat(e, fmt)}>
                {label}
              </button>
            );
          })}
        </div>
      )}
    </Link>
  );
}
