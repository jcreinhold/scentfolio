import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { Perfume } from "../types";
import { sortPerfumes, type SortKey, type SortDir } from "../lib/perfumeSort";

interface Column { key: SortKey; label: string; numeric?: boolean; }

const COLUMNS: Column[] = [
  { key: "name", label: "Name" },
  { key: "house", label: "House" },
  { key: "year", label: "Year", numeric: true },
  { key: "family", label: "Family" },
];

export default function PerfumeTable({ perfumes }: { perfumes: Perfume[] }) {
  const nav = useNavigate();
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const rows = useMemo(() => sortPerfumes(perfumes, sortKey, sortDir), [perfumes, sortKey, sortDir]);

  function onSort(key: SortKey) {
    if (key === sortKey) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(key); setSortDir("asc"); }
  }

  function ariaSort(key: SortKey): "ascending" | "descending" | "none" {
    if (key !== sortKey) return "none";
    return sortDir === "asc" ? "ascending" : "descending";
  }

  function SortHead({ col }: { col: Column }) {
    const active = col.key === sortKey;
    return (
      <th aria-sort={ariaSort(col.key)} className={col.numeric ? "num" : undefined}>
        <button type="button" className={`th-sort${active ? " active" : ""}`} onClick={() => onSort(col.key)}>
          {col.label}
          <span className="th-arrow" aria-hidden>{active ? (sortDir === "asc" ? "▲" : "▼") : ""}</span>
        </button>
      </th>
    );
  }

  return (
    <div className="table-wrap">
      <table className="perfume-table">
        <thead>
          <tr>
            {COLUMNS.map((c) => <SortHead key={c.key} col={c} />)}
            <th>Sizes</th>
            <SortHead col={{ key: "notes", label: "Notes", numeric: true }} />
          </tr>
        </thead>
        <tbody>
          {rows.map((p) => (
            <tr key={p.id} onClick={() => nav(`/perfume/${p.id}`)}>
              <td className="pt-name">
                <Link to={`/perfume/${p.id}`} onClick={(e) => e.stopPropagation()}>{p.name}</Link>
              </td>
              <td>{p.house || "—"}</td>
              <td className="num">{p.year ?? "—"}</td>
              <td>{p.scent_family ?? "—"}</td>
              <td>
                {p.formats.length === 0 ? <span className="pt-muted">—</span>
                  : p.formats.map((f) => <span key={f} className="chip pt-size">{f}</span>)}
              </td>
              <td className="num">{p.notes.length}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
