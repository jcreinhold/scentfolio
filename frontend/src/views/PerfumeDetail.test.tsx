import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { vi, it, expect } from "vitest";
import PerfumeDetail from "./PerfumeDetail";
import * as api from "../api";

const perfume = {
  id: 1, name: "Aventus", house: "Creed", perfumer: "Olivier Creed", year: 2010,
  scent_families: ["Chypre", "Woody"], description: "Smoky.", my_impressions: "old note",
  formats: ["full"], source_urls: [], notes: [
    { id: 1, name: "bergamot", tier: "top" }, { id: 2, name: "birch", tier: "heart" }],
};

it("shows pyramid and saves impressions", async () => {
  vi.spyOn(api, "getPerfume").mockResolvedValue(perfume as any);
  const upd = vi.spyOn(api, "updatePerfume").mockResolvedValue({ ...perfume, my_impressions: "new" } as any);
  render(<MemoryRouter initialEntries={["/perfume/1"]}>
    <Routes><Route path="/perfume/:id" element={<PerfumeDetail />} /></Routes>
  </MemoryRouter>);
  await waitFor(() => expect(screen.getByText("Aventus")).toBeInTheDocument());
  expect(screen.getByText("bergamot")).toBeInTheDocument();
  expect(screen.getByText("Chypre")).toBeInTheDocument();
  expect(screen.getByText("Woody")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText(/impressions/i), { target: { value: "new" } });
  fireEvent.click(screen.getByText(/save impressions/i));
  await waitFor(() => expect(upd).toHaveBeenCalledWith(1, { my_impressions: "new" }));
});

it("removes the perfume and navigates home when confirmed", async () => {
  vi.spyOn(api, "getPerfume").mockResolvedValue(perfume as any);
  const del = vi.spyOn(api, "deletePerfume").mockResolvedValue(undefined);
  vi.spyOn(window, "confirm").mockReturnValue(true);
  render(<MemoryRouter initialEntries={["/perfume/1"]}>
    <Routes>
      <Route path="/perfume/:id" element={<PerfumeDetail />} />
      <Route path="/" element={<div>Collection Home</div>} />
    </Routes>
  </MemoryRouter>);
  await waitFor(() => expect(screen.getByText("Aventus")).toBeInTheDocument());
  fireEvent.click(screen.getByText(/remove from collection/i));
  await waitFor(() => expect(del).toHaveBeenCalledWith(1));
  await waitFor(() => expect(screen.getByText("Collection Home")).toBeInTheDocument());
});
