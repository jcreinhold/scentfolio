import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { lookupPerfume, checkDuplicate, createPerfume } from "../api";
import SourceLinks from "../components/SourceLinks";
import { mapPool } from "../lib/mapPool";
import { errorMessage } from "../lib/useRequest";
import type { Draft, PerfumeStatus } from "../types";

const LOOKUP_CONCURRENCY = 4;
const SAVE_CONCURRENCY = 4;

type Status = "loading" | "success" | "error";
type SaveState = "saving" | "saved" | "error";
export type AddAction = "lookup" | "save" | null;

interface Row {
  name: string;
  status: Status;
  draft?: Draft;
  duplicate?: boolean;
  error?: string;
  kept: boolean;
  saveState?: SaveState;
  saveError?: string;
}

function parseNames(text: string): string[] {
  const seen = new Set<string>();
  const names: string[] = [];
  for (const line of text.split("\n")) {
    const name = line.trim();
    if (!name) continue;
    const key = name.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    names.push(name);
  }
  return names;
}

export default function BatchAdd({
  status,
  action,
  onAction,
}: {
  status: PerfumeStatus;
  action: AddAction;
  onAction: (action: AddAction) => void;
}) {
  const [text, setText] = useState("");
  const [rows, setRows] = useState<Row[] | null>(null);
  const [saved, setSaved] = useState<{
    count: number;
    status: PerfumeStatus;
  } | null>(null);
  const run = useRef<AbortController | null>(null);
  useEffect(() => () => run.current?.abort(), []);
  const names = parseNames(text);

  function update(index: number, patch: Partial<Row>) {
    setRows(
      (prev) =>
        prev && prev.map((r, i) => (i === index ? { ...r, ...patch } : r)),
    );
  }

  async function lookupAll() {
    if (action || names.length === 0) return;
    const controller = new AbortController();
    run.current = controller;
    const { signal } = controller;
    setSaved(null);
    onAction("lookup");
    setRows(names.map((name) => ({ name, status: "loading", kept: false })));

    await mapPool(
      names,
      LOOKUP_CONCURRENCY,
      async (name) => {
        const draft = await lookupPerfume(name, signal);
        signal.throwIfAborted();
        let duplicate = false;
        try {
          duplicate = (
            await checkDuplicate(draft.perfume.name, draft.perfume.house)
          ).duplicate;
        } catch {
          /* non-fatal — save without a flag */
        }
        return { draft, duplicate };
      },
      (i, res) => {
        if (res.ok) {
          update(i, {
            status: "success",
            kept: true,
            draft: res.value.draft,
            duplicate: res.value.duplicate,
          });
        } else {
          update(i, {
            status: "error",
            kept: false,
            error: errorMessage(res.error, "Lookup failed"),
          });
        }
      },
      signal,
    );

    if (!signal.aborted) onAction(null);
  }

  async function saveAll() {
    if (action || !rows) return;
    const toSave = rows
      .map((r, i) => ({ r, i }))
      .filter(
        ({ r }) => r.status === "success" && r.kept && r.saveState !== "saved",
      );
    if (toSave.length === 0) return;

    const controller = new AbortController();
    run.current = controller;
    const { signal } = controller;
    onAction("save");
    toSave.forEach(({ i }) =>
      update(i, { saveState: "saving", saveError: undefined }),
    );

    const results = await mapPool(
      toSave,
      SAVE_CONCURRENCY,
      async ({ r }) => {
        await createPerfume({ ...r.draft!.perfume, status });
      },
      (poolIdx, res) => {
        const { i } = toSave[poolIdx];
        if (res.ok) update(i, { saveState: "saved" });
        else
          update(i, {
            saveState: "error",
            saveError: errorMessage(res.error, "Save failed"),
          });
      },
      signal,
    );

    if (!signal.aborted) {
      setSaved({ count: results.filter((r) => r.ok).length, status });
      onAction(null);
    }
  }

  const selected =
    rows?.filter(
      (r) => r.status === "success" && r.kept && r.saveState !== "saved",
    ).length ?? 0;

  return (
    <div>
      <textarea
        className="search"
        style={{ minHeight: 120, fontFamily: "inherit" }}
        placeholder={
          "One perfume name per line…\nAventus\nSauvage\nBaccarat Rouge 540"
        }
        value={text}
        disabled={action !== null}
        onChange={(e) => setText(e.target.value)}
      />
      <button
        onClick={lookupAll}
        disabled={action !== null || names.length === 0}
        style={{ marginTop: 8 }}
      >
        {action === "lookup" ? "Looking up…" : `Look up all (${names.length})`}
      </button>

      {saved !== null && (
        <p style={{ color: "#15803d" }}>
          ✓ Added {saved.count} {saved.count === 1 ? "perfume" : "perfumes"} to{" "}
          {saved.status === "saved" ? "Saved" : "your collection"}.{" "}
          <Link to={saved.status === "saved" ? "/saved" : "/"}>
            {saved.status === "saved" ? "View Saved" : "View collection"}
          </Link>
        </p>
      )}

      {rows && (
        <div style={{ marginTop: 16 }}>
          <div className="card-top" style={{ marginBottom: 8 }}>
            <span className="label" style={{ marginTop: 0 }}>
              Review results
            </span>
            <button
              onClick={saveAll}
              disabled={action !== null || selected === 0}
            >
              {action === "save" ? "Saving…" : `Save ${selected} selected`}
            </button>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {rows.map((r, i) => (
              <div key={i} className="batch-row" data-status={r.status}>
                {r.status === "loading" && (
                  <span>
                    ⏳ <b>{r.name}</b> — looking up…
                  </span>
                )}
                {r.status === "error" && (
                  <span style={{ color: "crimson" }}>
                    ✕ <b>{r.name}</b> — {r.error}
                  </span>
                )}
                {r.status === "success" && r.draft && (
                  <>
                    <label
                      style={{
                        display: "flex",
                        gap: 8,
                        alignItems: "baseline",
                        cursor: "pointer",
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={r.kept}
                        disabled={action === "save" || r.saveState === "saved"}
                        onChange={(e) => update(i, { kept: e.target.checked })}
                      />
                      <span style={{ flex: 1 }}>
                        <b>{r.draft.perfume.name}</b> · {r.draft.perfume.house}{" "}
                        <span className="chip">
                          {r.draft.confidence} confidence
                        </span>
                        {r.duplicate && (
                          <span style={{ color: "#b45309" }}>
                            {" · ⚠️ already in collection"}
                          </span>
                        )}
                        {r.saveState === "saved" && (
                          <span style={{ color: "#15803d" }}> · ✓ saved</span>
                        )}
                        {r.saveState === "error" && (
                          <span style={{ color: "crimson" }}>
                            {" "}
                            · save failed: {r.saveError}
                          </span>
                        )}
                        <div className="card-notes">
                          {r.draft.perfume.notes.slice(0, 5).map((n, j) => (
                            <span key={j} className="chip">
                              {n.name}
                            </span>
                          ))}
                        </div>
                      </span>
                    </label>
                    <SourceLinks urls={r.draft.perfume.source_urls} />
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
