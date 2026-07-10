import { render, screen, fireEvent, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { it, expect } from "vitest";
import PerfumeTable from "./PerfumeTable";
import type { Perfume } from "../types";

function p(over: Partial<Perfume>): Perfume {
  return {
    id: 0, name: "x", house: "h", perfumer: null, year: null,
    scent_families: [], description: "", my_impressions: "",
    formats: [], source_urls: [], notes: [], ...over,
  };
}

const list: Perfume[] = [
  p({ id: 1, name: "Sauvage", house: "Dior", year: 2015, scent_families: ["Fresh"],
      formats: ["full", "travel"], notes: [{ id: 1, name: "bergamot" }] }),
  p({ id: 2, name: "Aventus", house: "Creed", year: 2010, scent_families: ["Chypre", "Woody"],
      notes: [{ id: 1, name: "a" }, { id: 2, name: "b" }, { id: 3, name: "c" }] }),
];

function rowNames() {
  return screen.getAllByRole("row").slice(1).map((r) => within(r).getAllByRole("cell")[0].textContent);
}

it("renders a row per perfume with sizes and note counts", () => {
  render(<MemoryRouter><PerfumeTable perfumes={list} /></MemoryRouter>);
  expect(screen.getByText("Sauvage")).toBeInTheDocument();
  expect(screen.getByText("Aventus")).toBeInTheDocument();
  // note counts
  expect(screen.getByText("3")).toBeInTheDocument();
  // sizes rendered
  expect(screen.getByText("travel")).toBeInTheDocument();
});

it("defaults to name-ascending and re-sorts when a header is clicked", () => {
  render(<MemoryRouter><PerfumeTable perfumes={list} /></MemoryRouter>);
  expect(rowNames()).toEqual(["Aventus", "Sauvage"]); // name asc

  fireEvent.click(screen.getByRole("button", { name: /year/i }));
  expect(rowNames()).toEqual(["Aventus", "Sauvage"]); // year asc: 2010, 2015

  fireEvent.click(screen.getByRole("button", { name: /year/i })); // toggle desc
  expect(rowNames()).toEqual(["Sauvage", "Aventus"]);
});

it("links each name to its detail page", () => {
  render(<MemoryRouter><PerfumeTable perfumes={list} /></MemoryRouter>);
  expect(screen.getByRole("link", { name: "Aventus" })).toHaveAttribute("href", "/perfume/2");
});

it("shows perfumers with a collection count and sorts by frequency", () => {
  const withPerfumers: Perfume[] = [
    p({ id: 1, name: "Solo", perfumer: "Lone Nose" }),
    p({ id: 2, name: "Twin A", perfumer: "Alberto Morillas" }),
    p({ id: 3, name: "Twin B", perfumer: "Alberto Morillas" }),
  ];
  render(<MemoryRouter><PerfumeTable perfumes={withPerfumers} /></MemoryRouter>);
  // Both rows from the twice-owned perfumer show a ×2 count badge; the singleton doesn't.
  expect(screen.getAllByText("×2")).toHaveLength(2);

  fireEvent.click(screen.getByRole("button", { name: /perfumer/i })); // asc: least-owned first
  expect(rowNames()).toEqual(["Solo", "Twin A", "Twin B"]);

  fireEvent.click(screen.getByRole("button", { name: /perfumer/i })); // desc: most-owned first
  expect(rowNames()).toEqual(["Twin A", "Twin B", "Solo"]);
});
