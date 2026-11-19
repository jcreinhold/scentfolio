import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { vi, it, expect } from "vitest";
import NoteDetail from "./NoteDetail";
import * as api from "../api";

it("shows note info and perfumes containing it", async () => {
  vi.spyOn(api, "getNote").mockResolvedValue({
    name: "bergamot",
    family: "Citrus",
    description: "Bright citrus.",
    origin: "natural",
    production: "Cold-pressed from the peel.",
    compounds: "",
    sourcing: "Calabria, Italy",
    proprietary_to: "",
    history: "Named after the town of Bergamo.",
    perfumes: [{ id: 1, name: "Sauvage", house: "Dior" }],
  });
  render(
    <MemoryRouter initialEntries={["/note/bergamot"]}>
      <Routes>
        <Route path="/note/:name" element={<NoteDetail />} />
      </Routes>
    </MemoryRouter>,
  );
  await waitFor(() => expect(screen.getByText("bergamot")).toBeInTheDocument());
  expect(screen.getByText("Bright citrus.")).toBeInTheDocument();
  expect(screen.getByText("natural")).toBeInTheDocument();
  expect(screen.getByText("Cold-pressed from the peel.")).toBeInTheDocument();
  expect(screen.getByText("Calabria, Italy")).toBeInTheDocument(); // sourcing section
  expect(
    screen.getByText("Named after the town of Bergamo."),
  ).toBeInTheDocument(); // history
  expect(screen.getByText(/Sauvage/)).toBeInTheDocument();
});

it("shows the missing-note error instead of staying in the loading state", async () => {
  vi.spyOn(api, "getNote").mockRejectedValue(new Error("Note not found"));
  render(
    <MemoryRouter initialEntries={["/note/unknown"]}>
      <Routes>
        <Route path="/note/:name" element={<NoteDetail />} />
      </Routes>
    </MemoryRouter>,
  );
  expect(screen.getByRole("status")).toHaveTextContent("Loading");
  expect(await screen.findByRole("alert")).toHaveTextContent("Note not found");
  expect(screen.queryByRole("status")).not.toBeInTheDocument();
});
