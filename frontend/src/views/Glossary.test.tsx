import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { it, expect, vi, beforeEach } from "vitest";
import Glossary from "./Glossary";
import * as api from "../api";

beforeEach(() => vi.restoreAllMocks());

const enriched = {
  id: 1,
  name: "bergamot",
  family: "Citrus",
  description: "Bright, zesty citrus.",
  origin: "natural",
  production: "Cold-pressed from the fruit peel in Calabria.",
  compounds: "",
  sourcing: "Calabria, Italy",
  proprietary_to: "",
  history: "",
  needs_enrichment: false,
};
const captive = {
  id: 3,
  name: "akigalawood",
  family: "Woody",
  description: "Woody peppery.",
  origin: "synthetic",
  production: "Biotech fractionation of patchouli.",
  compounds: "patchouli fraction",
  sourcing: "",
  proprietary_to: "Givaudan",
  history: "",
  needs_enrichment: false,
};
const blank = {
  id: 2,
  name: "ambroxan",
  family: "Woody",
  description: "",
  origin: "",
  production: "",
  compounds: "",
  sourcing: "",
  proprietary_to: "",
  history: "",
  needs_enrichment: true,
};

it("renders description, origin chip, sourcing, and a proprietary badge", async () => {
  vi.spyOn(api, "listNotes").mockResolvedValue([enriched, captive, blank]);
  render(
    <MemoryRouter>
      <Glossary />
    </MemoryRouter>,
  );
  await waitFor(() => expect(screen.getByText("bergamot")).toBeInTheDocument());
  expect(screen.getByText("Bright, zesty citrus.")).toBeInTheDocument();
  expect(screen.getByText("natural")).toBeInTheDocument();
  expect(screen.getByText(/calabria, italy/i)).toBeInTheDocument(); // sourcing line
  expect(screen.getByText("Givaudan")).toBeInTheDocument(); // proprietary badge
  expect(screen.getByText(/patchouli fraction/i)).toBeInTheDocument(); // compounds line
});

it("counts the server's enrichment candidates even when they have origins", async () => {
  vi.spyOn(api, "listNotes").mockResolvedValue([
    { ...enriched, needs_enrichment: true },
    { ...captive, needs_enrichment: true },
    { ...blank, needs_enrichment: false },
  ]);
  render(
    <MemoryRouter>
      <Glossary />
    </MemoryRouter>,
  );
  await waitFor(() =>
    expect(screen.getByText(/enrich notes \(2\)/i)).toBeInTheDocument(),
  );
});

it("enriches notes and re-fetches the list", async () => {
  const list = vi
    .spyOn(api, "listNotes")
    .mockResolvedValueOnce([enriched, blank]) // initial
    .mockResolvedValueOnce([
      enriched,
      {
        ...blank,
        origin: "synthetic",
        production: "Made from sclareol.",
        needs_enrichment: false,
      },
    ]); // after enrich
  const gen = vi
    .spyOn(api, "enrichMissingNotes")
    .mockResolvedValue({ updated: 1, remaining: 0 });

  render(
    <MemoryRouter>
      <Glossary />
    </MemoryRouter>,
  );
  await waitFor(() =>
    expect(screen.getByText(/enrich notes \(1\)/i)).toBeInTheDocument(),
  );

  fireEvent.click(screen.getByText(/enrich notes/i));
  await waitFor(() => expect(gen).toHaveBeenCalledTimes(1));
  await waitFor(() =>
    expect(screen.getByText("Made from sclareol.")).toBeInTheDocument(),
  );
  expect(list).toHaveBeenCalledTimes(2);
  // Nothing missing now → button gone.
  expect(screen.queryByText(/enrich notes/i)).not.toBeInTheDocument();
});
