import { useCallback, useEffect, useState } from "react";
import { listPerfumes, deletePerfume, updatePerfume } from "../api";
import type { PerfumeSort, PerfumeSortKey, PerfumeStatus } from "../types";
import PerfumeCard from "../components/PerfumeCard";
import PerfumeTable from "../components/PerfumeTable";
import { useViewMode, type ViewMode } from "../lib/useViewMode";
import { FAMILIES } from "../lib/families";
import { errorMessage, useRequest } from "../lib/useRequest";

const PAGE_SIZE = 40;
const EMPTY_FILTERS = { q: "", family: "", fmt: "" };

const COPY = {
  collection: {
    eyebrow: "The Collection",
    title: "Your fragrance wardrobe",
    unit: "on the shelf",
    emptyTitle: "Your shelf is empty",
    emptyBody: "Add your first scent to begin the archive.",
  },
  saved: {
    eyebrow: "Saved",
    title: "Fragrances you're tracking",
    unit: "saved · considering or familiar",
    emptyTitle: "Nothing saved yet",
    emptyBody:
      "Save fragrances you're considering or familiar with from the Add page.",
  },
} as const;

export default function Collection({
  status = "collection",
}: {
  status?: PerfumeStatus;
}) {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [page, setPage] = useState(0);
  const [sort, setSort] = useState<PerfumeSort>({
    key: "name",
    direction: "asc",
  });
  const [view, setView] = useViewMode();
  const [pendingRows, setPendingRows] = useState<Set<number>>(new Set());
  const [mutationError, setMutationError] = useState("");
  const copy = COPY[status];
  const { q, family, fmt } = filters;
  const load = useCallback(
    (signal: AbortSignal) =>
      listPerfumes(
        {
          ...filters,
          status,
          limit: PAGE_SIZE,
          offset: page * PAGE_SIZE,
          sort: view === "table" ? sort : undefined,
        },
        signal,
      ),
    [filters, status, page, view, sort],
  );
  const { result, reload } = useRequest(load);
  const total = result.status === "ready" ? result.data.total : null;
  const lastPage = Math.max(0, Math.ceil((total ?? 0) / PAGE_SIZE) - 1);

  useEffect(() => {
    if (total !== null && page > lastPage) setPage(lastPage);
  }, [total, page, lastPage]);

  function changeFilters(next: Partial<typeof filters>) {
    setFilters((current) => ({ ...current, ...next }));
    setPage(0);
  }

  function changeView(next: ViewMode) {
    setView(next);
    setPage(0);
  }

  function changeSort(key: PerfumeSortKey) {
    setSort((current) => ({
      key,
      direction:
        key === current.key && current.direction === "asc" ? "desc" : "asc",
    }));
    setPage(0);
  }

  async function changePerfume(id: number, save: () => Promise<unknown>) {
    if (pendingRows.has(id)) return;
    setMutationError("");
    setPendingRows((current) => new Set(current).add(id));
    try {
      await save();
      reload();
    } catch (error) {
      setMutationError(
        errorMessage(error, "Could not save the perfume change."),
      );
    } finally {
      setPendingRows((current) => {
        const next = new Set(current);
        next.delete(id);
        return next;
      });
    }
  }

  const filtering = Boolean(q || family || fmt);

  return (
    <div>
      <div className="collection-head">
        <div className="page-head">
          <div className="eyebrow">{copy.eyebrow}</div>
          <h2>{copy.title}</h2>
          <div className="page-sub">
            {total !== null && (
              <>
                {total} {total === 1 ? "scent" : "scents"}
                {filtering ? " matching your filters" : ` ${copy.unit}`}
              </>
            )}
          </div>
        </div>
        <div className="head-actions">
          {total !== null && total > 0 && (
            <a
              className="export-link"
              href={`/api/perfumes/export.csv?status=${status}`}
            >
              Export CSV
            </a>
          )}
          <div
            role="tablist"
            aria-label="Collection view"
            className="view-toggle"
          >
            <button
              role="tab"
              aria-selected={view === "cards"}
              disabled={view === "cards"}
              onClick={() => changeView("cards")}
            >
              Cards
            </button>
            <button
              role="tab"
              aria-selected={view === "table"}
              disabled={view === "table"}
              onClick={() => changeView("table")}
            >
              Table
            </button>
          </div>
        </div>
      </div>

      <input
        className="search"
        placeholder="Search names or notes…"
        value={q}
        onChange={(e) => changeFilters({ q: e.target.value })}
      />
      <div className="filters">
        <select
          aria-label="Filter by family"
          value={family}
          onChange={(e) => changeFilters({ family: e.target.value })}
        >
          <option value="">All families</option>
          {FAMILIES.map((f) => (
            <option key={f} value={f}>
              {f}
            </option>
          ))}
        </select>
        <select
          aria-label="Filter by format"
          value={fmt}
          onChange={(e) => changeFilters({ fmt: e.target.value })}
        >
          <option value="">All formats</option>
          <option value="full">Full</option>
          <option value="travel">Travel</option>
          <option value="sample">Sample</option>
        </select>
      </div>

      {mutationError && <p role="alert">{mutationError}</p>}
      {result.status === "failed" ? (
        <p role="alert">{result.error}</p>
      ) : result.status === "loading" || page > lastPage ? (
        <p role="status">Loading fragrances…</p>
      ) : result.data.perfumes.length === 0 ? (
        <div className="empty">
          <div className="empty-title">
            {filtering ? "Nothing matches" : copy.emptyTitle}
          </div>
          <div>{filtering ? "Try loosening a filter." : copy.emptyBody}</div>
        </div>
      ) : view === "table" ? (
        <PerfumeTable
          perfumes={result.data.perfumes}
          sort={sort}
          onSort={changeSort}
        />
      ) : (
        <div className="grid">
          {result.data.perfumes.map((p) => (
            <PerfumeCard
              key={p.id}
              p={p}
              pending={pendingRows.has(p.id)}
              onDelete={(id) => changePerfume(id, () => deletePerfume(id))}
              onSetFormats={(id, formats) =>
                changePerfume(id, () => updatePerfume(id, { formats }))
              }
            />
          ))}
        </div>
      )}
      {result.status === "ready" && lastPage > 0 && page <= lastPage && (
        <nav className="filters" aria-label="Collection pages">
          <button onClick={() => setPage(page - 1)} disabled={page === 0}>
            Previous
          </button>
          <span>
            Page {page + 1} of {lastPage + 1}
          </span>
          <button
            onClick={() => setPage(page + 1)}
            disabled={page === lastPage}
          >
            Next
          </button>
        </nav>
      )}
    </div>
  );
}
