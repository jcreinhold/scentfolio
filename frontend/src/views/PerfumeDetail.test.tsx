import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { vi, it, expect } from "vitest";
import PerfumeDetail from "./PerfumeDetail";
import * as api from "../api";
import type { Perfume } from "../types";

const perfume: Perfume = {
  id: 1,
  name: "Aventus",
  status: "saved",
  house: "Creed",
  perfumer: "Olivier Creed",
  year: 2010,
  scent_families: ["Chypre", "Woody"],
  description: "Smoky.",
  my_impressions: "old note",
  formats: ["full"],
  source_urls: [],
  notes: [
    { id: 1, name: "bergamot", tier: "top" },
    { id: 2, name: "birch", tier: "heart" },
  ],
};

it("shows pyramid and saves impressions", async () => {
  vi.spyOn(api, "getPerfume").mockResolvedValue(perfume as any);
  const upd = vi
    .spyOn(api, "updatePerfume")
    .mockResolvedValue({ ...perfume, my_impressions: "new" } as any);
  render(
    <MemoryRouter initialEntries={["/perfume/1"]}>
      <Routes>
        <Route path="/perfume/:id" element={<PerfumeDetail />} />
      </Routes>
    </MemoryRouter>,
  );
  await waitFor(() => expect(screen.getByText("Aventus")).toBeInTheDocument());
  expect(screen.getByText("bergamot")).toBeInTheDocument();
  expect(screen.getByText("Chypre")).toBeInTheDocument();
  expect(screen.getByText("Woody")).toBeInTheDocument();
  expect(
    screen.queryByRole("group", { name: "Sources" }),
  ).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText(/impressions/i), {
    target: { value: "new" },
  });
  fireEvent.click(screen.getByText(/save impressions/i));
  await waitFor(() =>
    expect(upd).toHaveBeenCalledWith(1, { my_impressions: "new" }),
  );
});

it("adds and removes fragrance family tags", async () => {
  vi.spyOn(api, "getPerfume").mockResolvedValue(perfume);
  let stored = perfume;
  const upd = vi
    .spyOn(api, "updatePerfume")
    .mockImplementation(async (_id, patch) => {
      stored = { ...stored, ...patch };
      return stored;
    });
  render(
    <MemoryRouter initialEntries={["/perfume/1"]}>
      <Routes>
        <Route path="/perfume/:id" element={<PerfumeDetail />} />
      </Routes>
    </MemoryRouter>,
  );
  await waitFor(() => expect(screen.getByText("Aventus")).toBeInTheDocument());

  // Remove "Chypre" -> persists the remaining families.
  fireEvent.click(screen.getByLabelText("Remove Chypre family"));
  await waitFor(() =>
    expect(upd).toHaveBeenCalledWith(1, { scent_families: ["Woody"] }),
  );

  // Add "Gourmand" via the picker after the first change is confirmed.
  await waitFor(() =>
    expect(
      screen.queryByLabelText("Remove Chypre family"),
    ).not.toBeInTheDocument(),
  );
  fireEvent.change(screen.getByLabelText(/add fragrance family/i), {
    target: { value: "Gourmand" },
  });
  await waitFor(() =>
    expect(upd).toHaveBeenCalledWith(1, {
      scent_families: ["Woody", "Gourmand"],
    }),
  );
});

it("removes the perfume and navigates home when confirmed", async () => {
  vi.spyOn(api, "getPerfume").mockResolvedValue(perfume as any);
  const del = vi.spyOn(api, "deletePerfume").mockResolvedValue(undefined);
  vi.spyOn(window, "confirm").mockReturnValue(true);
  render(
    <MemoryRouter initialEntries={["/perfume/1"]}>
      <Routes>
        <Route path="/perfume/:id" element={<PerfumeDetail />} />
        <Route path="/" element={<div>Collection Home</div>} />
      </Routes>
    </MemoryRouter>,
  );
  await waitFor(() => expect(screen.getByText("Aventus")).toBeInTheDocument());
  fireEvent.click(screen.getByRole("button", { name: "Remove" }));
  await waitFor(() => expect(del).toHaveBeenCalledWith(1));
  await waitFor(() =>
    expect(screen.getByText("Collection Home")).toBeInTheDocument(),
  );
});

it("moves a saved perfume into the collection", async () => {
  const sourceUrl = "http://example.test/archive/aventus";
  vi.spyOn(api, "getPerfume").mockResolvedValue({
    ...perfume,
    source_urls: [sourceUrl],
  } as any);
  const upd = vi
    .spyOn(api, "updatePerfume")
    .mockResolvedValue({ ...perfume, status: "collection" } as any);
  render(
    <MemoryRouter initialEntries={["/perfume/1"]}>
      <Routes>
        <Route path="/perfume/:id" element={<PerfumeDetail />} />
      </Routes>
    </MemoryRouter>,
  );
  await waitFor(() => expect(screen.getByText("Aventus")).toBeInTheDocument());
  // Saved item shows the badge + a "Move to collection" action.
  expect(screen.getByText(/saved · not in collection/i)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: sourceUrl })).toHaveAttribute(
    "href",
    sourceUrl,
  );
  fireEvent.click(screen.getByRole("button", { name: /move to collection/i }));
  await waitFor(() =>
    expect(upd).toHaveBeenCalledWith(1, { status: "collection" }),
  );
});
