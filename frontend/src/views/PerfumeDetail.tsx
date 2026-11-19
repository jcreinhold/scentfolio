import { useCallback, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { getPerfume, updatePerfume, deletePerfume } from "../api";
import SourceLinks from "../components/SourceLinks";
import type { Perfume, PerfumePatch, Tier } from "../types";
import { FAMILIES } from "../lib/families";
import { errorMessage, useRequest } from "../lib/useRequest";

const TIERS: Tier[] = ["top", "heart", "base"];

export default function PerfumeDetail() {
  const { id } = useParams();
  return <PerfumeRecord key={id} id={Number(id)} />;
}

function PerfumeRecord({ id }: { id: number }) {
  const nav = useNavigate();
  const load = useCallback(
    (signal: AbortSignal) => getPerfume(id, signal),
    [id],
  );
  const { result } = useRequest(load);
  const [saved, setSaved] = useState<Perfume | null>(null);
  const [editedImpressions, setEditedImpressions] = useState<string | null>(
    null,
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  if (result.status === "loading") return <div role="status">Loading…</div>;
  if (result.status === "failed") return <p role="alert">{result.error}</p>;

  const p = saved ?? result.data;
  const impressions = editedImpressions ?? p.my_impressions;
  const available = FAMILIES.filter((f) => !p.scent_families.includes(f));

  async function change(save: () => Promise<void>) {
    if (saving) return;
    setSaving(true);
    setError("");
    try {
      await save();
    } catch (error) {
      setError(errorMessage(error, "Could not save the perfume change."));
    } finally {
      setSaving(false);
    }
  }

  function patch(patch: PerfumePatch) {
    return change(async () => {
      setSaved(await updatePerfume(id, patch));
    });
  }

  function remove() {
    if (window.confirm(`Remove ${p.name} from your collection?`)) {
      return change(async () => {
        await deletePerfume(id);
        nav("/");
      });
    }
  }

  return (
    <div>
      <div className="page-head">
        <div className="eyebrow">
          {p.status === "saved"
            ? "Saved · not in collection"
            : "From the archive"}
        </div>
        <h2>{p.name}</h2>
        <div className="card-sub">
          {p.house}
          {p.year ? ` · ${p.year}` : ""}
          {p.perfumer ? ` · Perfumer: ${p.perfumer}` : ""}
        </div>
        <div className="family-tags">
          {p.scent_families.map((f) => (
            <span key={f} className="family-tag family-tag-editable">
              <span>{f}</span>
              <button
                type="button"
                className="family-tag-remove"
                aria-label={`Remove ${f} family`}
                disabled={saving}
                onClick={() =>
                  patch({
                    scent_families: p.scent_families.filter((x) => x !== f),
                  })
                }
              >
                ×
              </button>
            </span>
          ))}
          {available.length > 0 && (
            <select
              className="family-add"
              aria-label="Add fragrance family"
              value=""
              disabled={saving}
              onChange={(e) => {
                if (e.target.value)
                  patch({
                    scent_families: [...p.scent_families, e.target.value],
                  });
              }}
            >
              <option value="">+ Add family</option>
              {available.map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      {error && <p role="alert">{error}</p>}
      <div className="label">Note pyramid</div>
      <div className="pyramid">
        {TIERS.map((tier) => (
          <div key={tier} className={tier}>
            <b>{tier}:</b>{" "}
            {p.notes
              .filter((n) => n.tier === tier)
              .map((n, i, arr) => (
                <span key={n.id}>
                  <Link to={`/note/${encodeURIComponent(n.name)}`}>
                    {n.name}
                  </Link>
                  {i < arr.length - 1 ? ", " : ""}
                </span>
              ))}
          </div>
        ))}
      </div>

      <div className="label">Description</div>
      <p>{p.description}</p>
      <SourceLinks urls={p.source_urls} />

      <div className="label">Formats</div>
      <div className="card-notes">
        {p.formats.map((f) => (
          <span key={f} className={`badge badge-${f}`}>
            {f}
          </span>
        ))}
      </div>

      <div className="label">
        <label htmlFor="imp">My impressions</label>
      </div>
      <textarea
        id="imp"
        aria-label="my impressions"
        className="search"
        value={impressions}
        onChange={(e) => setEditedImpressions(e.target.value)}
      />
      <button
        onClick={() => patch({ my_impressions: impressions })}
        disabled={saving}
        style={{ marginTop: 8 }}
      >
        Save impressions
      </button>

      <div
        style={{
          marginTop: 32,
          borderTop: "1px solid #eee",
          paddingTop: 16,
          display: "flex",
          gap: 10,
          flexWrap: "wrap",
        }}
      >
        <button
          disabled={saving}
          onClick={() =>
            patch({ status: p.status === "saved" ? "collection" : "saved" })
          }
        >
          {p.status === "saved" ? "Move to collection" : "Move to saved"}
        </button>
        <button className="btn-danger" onClick={remove} disabled={saving}>
          Remove
        </button>
      </div>
    </div>
  );
}
