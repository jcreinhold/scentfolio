import { Link, useNavigate } from "react-router-dom";
import type { Perfume, PerfumeSort, PerfumeSortKey } from "../types";

interface Column {
  key: PerfumeSortKey;
  label: string;
  numeric?: boolean;
}

const COLUMNS: Column[] = [
  { key: "name", label: "Name" },
  { key: "house", label: "House" },
  { key: "year", label: "Year", numeric: true },
  { key: "family", label: "Family" },
  { key: "perfumer", label: "Perfumer" },
];

export default function PerfumeTable({
  perfumes,
  sort,
  onSort,
}: {
  perfumes: Perfume[];
  sort: PerfumeSort;
  onSort: (key: PerfumeSortKey) => void;
}) {
  const nav = useNavigate();

  function sortHead(col: Column) {
    const active = col.key === sort.key;
    const ascending = sort.direction === "asc";
    return (
      <th
        key={col.key}
        aria-sort={
          active ? (ascending ? "ascending" : "descending") : undefined
        }
        className={col.numeric ? "num" : undefined}
      >
        <button
          type="button"
          className={`th-sort${active ? " active" : ""}`}
          onClick={() => onSort(col.key)}
        >
          {col.label}
          <span className="th-arrow" aria-hidden>
            {active ? (ascending ? "▲" : "▼") : ""}
          </span>
        </button>
      </th>
    );
  }

  return (
    <div className="table-wrap">
      <table className="perfume-table">
        <thead>
          <tr>
            {COLUMNS.map(sortHead)}
            <th>Sizes</th>
            {sortHead({ key: "notes", label: "Notes", numeric: true })}
          </tr>
        </thead>
        <tbody>
          {perfumes.map((p) => (
            <tr key={p.id} onClick={() => nav(`/perfume/${p.id}`)}>
              <td className="pt-name">
                <Link
                  to={`/perfume/${p.id}`}
                  onClick={(e) => e.stopPropagation()}
                >
                  {p.name}
                </Link>
              </td>
              <td>{p.house || "—"}</td>
              <td className="num">{p.year ?? "—"}</td>
              <td>
                {p.scent_families.length ? p.scent_families.join(" · ") : "—"}
              </td>
              <td>{p.perfumer || <span className="pt-muted">—</span>}</td>
              <td>
                {p.formats.length === 0 ? (
                  <span className="pt-muted">—</span>
                ) : (
                  p.formats.map((f) => (
                    <span key={f} className="chip pt-size">
                      {f}
                    </span>
                  ))
                )}
              </td>
              <td className="num">{p.notes.length}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
