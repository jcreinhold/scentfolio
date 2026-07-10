import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { it, expect, vi, beforeEach } from "vitest";
import Glossary from "./Glossary";
import * as api from "../api";

beforeEach(() => vi.restoreAllMocks());

const withDesc = { id: 1, name: "bergamot", family: "Citrus", description: "Bright, zesty citrus." };
const blank = { id: 2, name: "oud", family: "Woody", description: "" };

it("renders a note's description", async () => {
  vi.spyOn(api, "listNotes").mockResolvedValue([withDesc, blank]);
  render(<MemoryRouter><Glossary /></MemoryRouter>);
  await waitFor(() => expect(screen.getByText("bergamot")).toBeInTheDocument());
  expect(screen.getByText("Bright, zesty citrus.")).toBeInTheDocument();
});

it("shows a generate button counting the notes missing descriptions", async () => {
  vi.spyOn(api, "listNotes").mockResolvedValue([withDesc, blank]);
  render(<MemoryRouter><Glossary /></MemoryRouter>);
  await waitFor(() => expect(screen.getByText(/generate descriptions \(1\)/i)).toBeInTheDocument());
});

it("generates descriptions and re-fetches the list", async () => {
  const list = vi.spyOn(api, "listNotes")
    .mockResolvedValueOnce([withDesc, blank])                                  // initial load
    .mockResolvedValueOnce([withDesc, { ...blank, description: "Smoky resin." }]); // after generate
  const gen = vi.spyOn(api, "describeMissingNotes").mockResolvedValue({ updated: 1 });

  render(<MemoryRouter><Glossary /></MemoryRouter>);
  await waitFor(() => expect(screen.getByText(/generate descriptions \(1\)/i)).toBeInTheDocument());

  fireEvent.click(screen.getByText(/generate descriptions/i));
  await waitFor(() => expect(gen).toHaveBeenCalledTimes(1));
  await waitFor(() => expect(screen.getByText("Smoky resin.")).toBeInTheDocument());
  expect(list).toHaveBeenCalledTimes(2);
  // Nothing missing now → button gone.
  expect(screen.queryByText(/generate descriptions/i)).not.toBeInTheDocument();
});
