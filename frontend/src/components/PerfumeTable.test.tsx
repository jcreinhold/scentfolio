import { render, screen, fireEvent, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { it, expect, vi } from "vitest";
import PerfumeTable from "./PerfumeTable";
import type { Perfume, PerfumeSort } from "../types";

function p(over: Partial<Perfume>): Perfume {
  return {
    id: 0,
    name: "x",
    status: "collection",
    house: "h",
    perfumer: null,
    year: null,
    scent_families: [],
    description: "",
    my_impressions: "",
    formats: [],
    source_urls: [],
    notes: [],
    ...over,
  };
}

const list: Perfume[] = [
  p({
    id: 1,
    name: "Sauvage",
    house: "Dior",
    year: 2015,
    scent_families: ["Fresh"],
    formats: ["full", "travel"],
    notes: [{ id: 1, name: "bergamot" }],
  }),
  p({
    id: 2,
    name: "Aventus",
    house: "Creed",
    year: 2010,
    scent_families: ["Chypre", "Woody"],
    notes: [
      { id: 1, name: "a" },
      { id: 2, name: "b" },
      { id: 3, name: "c" },
    ],
  }),
];
const nameAscending: PerfumeSort = { key: "name", direction: "asc" };

function rowNames() {
  return screen
    .getAllByRole("row")
    .slice(1)
    .map((r) => within(r).getAllByRole("cell")[0].textContent);
}

it("renders a row per perfume with sizes and note counts", () => {
  render(
    <MemoryRouter>
      <PerfumeTable perfumes={list} sort={nameAscending} onSort={() => {}} />
    </MemoryRouter>,
  );
  expect(screen.getByText("Sauvage")).toBeInTheDocument();
  expect(screen.getByText("Aventus")).toBeInTheDocument();
  // note counts
  expect(screen.getByText("3")).toBeInTheDocument();
  // sizes rendered
  expect(screen.getByText("travel")).toBeInTheDocument();
});

it("keeps server order and sends header clicks to its caller", () => {
  const onSort = vi.fn();
  render(
    <MemoryRouter>
      <PerfumeTable
        perfumes={list}
        sort={{ key: "perfumer", direction: "desc" }}
        onSort={onSort}
      />
    </MemoryRouter>,
  );
  expect(rowNames()).toEqual(["Sauvage", "Aventus"]);
  expect(
    screen.getByRole("columnheader", { name: "Perfumer" }),
  ).toHaveAttribute("aria-sort", "descending");
  fireEvent.click(screen.getByRole("button", { name: /year/i }));
  expect(onSort).toHaveBeenCalledWith("year");
});

it("links each name to its detail page", () => {
  render(
    <MemoryRouter>
      <PerfumeTable perfumes={list} sort={nameAscending} onSort={() => {}} />
    </MemoryRouter>,
  );
  expect(screen.getByRole("link", { name: "Aventus" })).toHaveAttribute(
    "href",
    "/perfume/2",
  );
});
