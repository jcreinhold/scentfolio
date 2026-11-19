import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { lookupPerfume, createPerfume, checkDuplicate } from "../api";
import SourceLinks from "../components/SourceLinks";
import type { Draft, Format, PerfumeDraft, PerfumeStatus } from "../types";
import { errorMessage } from "../lib/useRequest";
import BatchAdd, { type AddAction } from "./BatchAdd";

const FORMATS: Format[] = ["full", "travel", "sample"];

export default function Add() {
  const [mode, setMode] = useState<"single" | "batch">("single");
  const [dest, setDest] = useState<PerfumeStatus>("collection");
  const [name, setName] = useState("");
  const [draft, setDraft] = useState<Draft | null>(null);
  const [error, setError] = useState("");
  const [action, setAction] = useState<AddAction>(null);
  const [dupWarning, setDupWarning] = useState(false);
  const nav = useNavigate();

  async function doLookup() {
    if (action || !name) return;
    setError("");
    setAction("lookup");
    setDraft(null);
    setDupWarning(false);
    try {
      const d = await lookupPerfume(name);
      setDraft(d);
      try {
        const dup = await checkDuplicate(d.perfume.name, d.perfume.house);
        setDupWarning(dup.duplicate);
      } catch {
        setDupWarning(false);
      }
    } catch (error) {
      setError(errorMessage(error, "Lookup failed"));
    } finally {
      setAction(null);
    }
  }

  function patch<K extends keyof PerfumeDraft>(
    field: K,
    value: PerfumeDraft[K],
  ) {
    if (!draft) return;
    setDraft({ ...draft, perfume: { ...draft.perfume, [field]: value } });
  }

  function toggleFormat(f: Format) {
    if (!draft) return;
    const has = draft.perfume.formats.includes(f);
    patch(
      "formats",
      has
        ? draft.perfume.formats.filter((x) => x !== f)
        : [...draft.perfume.formats, f],
    );
  }

  async function save() {
    if (!draft || action) return;
    setError("");
    setAction("save");
    try {
      const created = await createPerfume({ ...draft.perfume, status: dest });
      nav(`/perfume/${created.id}`);
    } catch (error) {
      setError(errorMessage(error, "Save failed"));
    } finally {
      setAction(null);
    }
  }

  return (
    <div>
      <div className="page-head">
        <div className="eyebrow">New Acquisition</div>
        <h2>Add a perfume</h2>
        <div className="page-sub">
          Look one up by name, or paste a whole list to add in bulk.
        </div>
      </div>

      <div className="add-dest">
        <span className="add-dest-label">Add to</span>
        <div role="tablist" aria-label="Destination" className="view-toggle">
          <button
            role="tab"
            aria-selected={dest === "collection"}
            disabled={dest === "collection" || action === "save"}
            onClick={() => setDest("collection")}
          >
            Collection
          </button>
          <button
            role="tab"
            aria-selected={dest === "saved"}
            disabled={dest === "saved" || action === "save"}
            onClick={() => setDest("saved")}
          >
            Saved
          </button>
        </div>
      </div>

      <div className="filters" role="tablist">
        <button
          role="tab"
          aria-selected={mode === "single"}
          disabled={mode === "single" || action !== null}
          onClick={() => setMode("single")}
        >
          One at a time
        </button>
        <button
          role="tab"
          aria-selected={mode === "batch"}
          disabled={mode === "batch" || action !== null}
          onClick={() => setMode("batch")}
        >
          Batch add
        </button>
      </div>

      {mode === "batch" ? (
        <BatchAdd status={dest} action={action} onAction={setAction} />
      ) : (
        <>
          <div style={{ display: "flex", gap: 8 }}>
            <input
              className="search"
              placeholder="Add a perfume by name…"
              value={name}
              disabled={action === "lookup"}
              onChange={(e) => setName(e.target.value)}
            />
            <button onClick={doLookup} disabled={action !== null || !name}>
              {action === "lookup" ? "Searching…" : "Look up"}
            </button>
          </div>
          {error && <p role="alert">{error}</p>}

          {draft && (
            <div>
              {dupWarning && (
                <p style={{ color: "#b45309" }}>
                  ⚠️ You already have a perfume with this name and house in your
                  collection.
                </p>
              )}
              <p className="label">
                {draft.confidence} confidence — verify against sources before
                saving
              </p>
              <input
                className="search"
                value={draft.perfume.name}
                onChange={(e) => patch("name", e.target.value)}
              />
              <input
                className="search"
                value={draft.perfume.house}
                onChange={(e) => patch("house", e.target.value)}
                placeholder="House"
              />
              <textarea
                className="search"
                value={draft.perfume.description}
                onChange={(e) => patch("description", e.target.value)}
              />
              <div className="filters">
                {FORMATS.map((f) => (
                  <label key={f}>
                    <input
                      type="checkbox"
                      checked={draft.perfume.formats.includes(f)}
                      onChange={() => toggleFormat(f)}
                    />{" "}
                    {f}
                  </label>
                ))}
              </div>
              <div className="card-notes">
                {draft.perfume.notes.map((n, i) => (
                  <span key={i} className="chip">
                    <span>{n.name}</span>
                    {n.tier ? ` (${n.tier})` : ""}
                  </span>
                ))}
              </div>
              <SourceLinks urls={draft.perfume.source_urls} />
              <button
                onClick={save}
                disabled={action !== null}
                style={{ marginTop: 12 }}
              >
                {action === "save"
                  ? "Saving…"
                  : dest === "saved"
                    ? "Save to Saved"
                    : "Save to collection"}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
