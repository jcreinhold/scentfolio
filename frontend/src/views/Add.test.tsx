import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi, it, expect } from "vitest";
import Add from "./Add";
import * as api from "../api";

it("looks up a name and shows the draft for confirmation", async () => {
  vi.spyOn(api, "lookupPerfume").mockResolvedValue({
    confidence: "high",
    perfume: { name: "Aventus", house: "Creed", perfumer: "Olivier Creed", year: 2010,
      scent_family: "Chypre", description: "Smoky.", my_impressions: "",
      formats: [], source_urls: ["https://x"], notes: [{ id: 0, name: "bergamot", tier: "top" }] },
  } as any);
  vi.spyOn(api, "checkDuplicate").mockResolvedValue({ duplicate: false, id: null });

  render(<MemoryRouter><Add /></MemoryRouter>);
  fireEvent.change(screen.getByPlaceholderText(/perfume by name/i), { target: { value: "Aventus" } });
  fireEvent.click(screen.getByText(/look up/i));

  await waitFor(() => expect(screen.getByDisplayValue("Aventus")).toBeInTheDocument());
  expect(screen.getByText(/high confidence/i)).toBeInTheDocument();
  expect(screen.getByText("bergamot")).toBeInTheDocument();
});

it("warns when the looked-up perfume is already in the collection", async () => {
  vi.spyOn(api, "lookupPerfume").mockResolvedValue({
    confidence: "medium",
    perfume: { name: "Aventus", house: "Creed", perfumer: null, year: null,
      scent_family: "Chypre", description: "", my_impressions: "",
      formats: [], source_urls: [], notes: [] },
  } as any);
  vi.spyOn(api, "checkDuplicate").mockResolvedValue({ duplicate: true, id: 1 });
  render(<MemoryRouter><Add /></MemoryRouter>);
  fireEvent.change(screen.getByPlaceholderText(/perfume by name/i), { target: { value: "Aventus" } });
  fireEvent.click(screen.getByText(/look up/i));
  await waitFor(() => expect(screen.getByText(/already have a perfume/i)).toBeInTheDocument());
});
