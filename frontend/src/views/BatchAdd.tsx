import { useState } from "react";
import { Link } from "react-router-dom";
import { lookupPerfume, checkDuplicate, createPerfume } from "../api";
import { mapPool } from "../lib/mapPool";
import type { Draft } from "../types";

const LOOKUP_CONCURRENCY = 4;
const SAVE_CONCURRENCY = 4;

type Status = "loading" | "success" | "error";
type SaveState = "saving" | "saved" | "error";

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
  status = "collection",
}: {
  status?: string;
}) {
  const [text, setText] = useState("");
  const [rows, setRows] = useState<Row[] | null>(null);
  const [running, setRunning] = useState(false);
  const [savedCount, setSavedCount] = useState<number | null>(null);

  function update(index: number, patch: Partial<Row>) {
    setRows(
      (prev) =>
        prev && prev.map((r, i) => (i === index ? { ...r, ...patch } : r)),
    );
  }

  async function lookupAll() {
    const names = parseNames(text);
    if (names.length === 0) return;
    setSavedCount(null);
    setRunning(true);
    setRows(names.map((name) => ({ name, status: "loading", kept: false })));

    await mapPool(
      names,
      LOOKUP_CONCURRENCY,
      async (name) => {
        const draft = await lookupPerfume(name);
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
            error: (res.error as Error)?.message ?? "Lookup failed",
          });
        }
      },
    );

    setRunning(false);
  }

  async function saveAll() {
    if (!rows) return;
    const toSave = rows
      .map((r, i) => ({ r, i }))
      .filter(
        ({ r }) => r.status === "success" && r.kept && r.saveState !== "saved",
      );
    if (toSave.length === 0) return;

    setRunning(true);
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
            saveError: (res.error as Error)?.message ?? "Save failed",
          });
      },
    );

    setSavedCount(results.filter((r) => r.ok).length);
    setRunning(false);
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
        onChange={(e) => setText(e.target.value)}
      />
      <button
        onClick={lookupAll}
        disabled={running || parseNames(text).length === 0}
        style={{ marginTop: 8 }}
      >
        {running && !savedCount
          ? "Looking up…"
          : `Look up all (${parseNames(text).length})`}
      </button>

      {savedCount !== null && (
        <p style={{ color: "#15803d" }}>
          ✓ Added {savedCount} {savedCount === 1 ? "perfume" : "perfumes"} to
          your collection. <Link to="/">View collection</Link>
        </p>
      )}

      {rows && (
        <div style={{ marginTop: 16 }}>
          <div className="card-top" style={{ marginBottom: 8 }}>
            <span className="label" style={{ marginTop: 0 }}>
              Review results
            </span>
            <button onClick={saveAll} disabled={running || selected === 0}>
              Save {selected} selected
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
                      disabled={r.saveState === "saved"}
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
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
