import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { it, expect, vi, beforeEach } from "vitest";
import Glossary from "./Glossary";
import * as api from "../api";

beforeEach(() => vi.restoreAllMocks());

const enriched = {
  id: 1, name: "bergamot", family: "Citrus", description: "Bright, zesty citrus.",
  origin: "natural", production: "Cold-pressed from the fruit peel in Calabria.",
};
const blank = { id: 2, name: "ambroxan", family: "Woody", description: "", origin: "", production: "" };

it("renders a note's description, origin chip, and production fact", async () => {
  vi.spyOn(api, "listNotes").mockResolvedValue([enriched, blank]);
  render(<MemoryRouter><Glossary /></MemoryRouter>);
  await waitFor(() => expect(screen.getByText("bergamot")).toBeInTheDocument());
  expect(screen.getByText("Bright, zesty citrus.")).toBeInTheDocument();
  expect(screen.getByText("natural")).toBeInTheDocument();
  expect(screen.getByText(/cold-pressed from the fruit peel/i)).toBeInTheDocument();
});

it("shows an enrich button counting notes missing an origin", async () => {
  vi.spyOn(api, "listNotes").mockResolvedValue([enriched, blank]);
  render(<MemoryRouter><Glossary /></MemoryRouter>);
  await waitFor(() => expect(screen.getByText(/enrich notes \(1\)/i)).toBeInTheDocument());
});

it("enriches notes and re-fetches the list", async () => {
  const list = vi.spyOn(api, "listNotes")
    .mockResolvedValueOnce([enriched, blank])                                             // initial
    .mockResolvedValueOnce([enriched, { ...blank, origin: "synthetic",
                                        production: "Made from sclareol." }]);            // after enrich
  const gen = vi.spyOn(api, "enrichMissingNotes").mockResolvedValue({ updated: 1 });

  render(<MemoryRouter><Glossary /></MemoryRouter>);
  await waitFor(() => expect(screen.getByText(/enrich notes \(1\)/i)).toBeInTheDocument());

  fireEvent.click(screen.getByText(/enrich notes/i));
  await waitFor(() => expect(gen).toHaveBeenCalledTimes(1));
  await waitFor(() => expect(screen.getByText("Made from sclareol.")).toBeInTheDocument());
  expect(list).toHaveBeenCalledTimes(2);
  // Nothing missing now → button gone.
  expect(screen.queryByText(/enrich notes/i)).not.toBeInTheDocument();
});
