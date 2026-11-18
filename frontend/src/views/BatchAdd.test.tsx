import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi, it, expect, beforeEach } from "vitest";
import BatchAdd from "./BatchAdd";
import * as api from "../api";

function draftFor(name: string, sourceUrls: string[] = []) {
  return {
    confidence: "high",
    perfume: {
      name,
      house: "House",
      perfumer: null,
      year: null,
      scent_families: ["Fresh"],
      description: "",
      my_impressions: "",
      formats: [],
      source_urls: sourceUrls,
      notes: [],
    },
  } as any;
}

beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(api, "checkDuplicate").mockResolvedValue({
    duplicate: false,
    id: null,
  });
});

it("looks up every pasted name (de-duplicated) and lists results", async () => {
  const sourceUrl = "https://example.test/aventus";
  const lookup = vi
    .spyOn(api, "lookupPerfume")
    .mockImplementation(async (n: string) =>
      draftFor(n, n === "Aventus" ? [sourceUrl] : []),
    );
  render(
    <MemoryRouter>
      <BatchAdd />
    </MemoryRouter>,
  );

  fireEvent.change(screen.getByPlaceholderText(/one perfume name per line/i), {
    target: { value: "Aventus\nSauvage\nAventus\n\n" },
  });
  fireEvent.click(screen.getByText(/look up all/i));

  await waitFor(() => expect(screen.getByText("Aventus")).toBeInTheDocument());
  expect(screen.getByText("Sauvage")).toBeInTheDocument();
  const source = screen.getByRole("link", { name: sourceUrl });
  expect(source).toHaveAttribute("href", sourceUrl);
  expect(source.closest("label")).toBeNull();
  expect(source.closest(".batch-row")).toHaveTextContent("Aventus");
  expect(screen.getAllByRole("group", { name: "Sources" })).toHaveLength(1);
  // "Aventus" appears once despite being listed twice.
  expect(lookup).toHaveBeenCalledTimes(2);
});

it("saves only the kept rows and reports the count", async () => {
  vi.spyOn(api, "lookupPerfume").mockImplementation(async (n: string) =>
    draftFor(n),
  );
  const create = vi.spyOn(api, "createPerfume").mockResolvedValue({} as any);
  render(
    <MemoryRouter>
      <BatchAdd />
    </MemoryRouter>,
  );

  fireEvent.change(screen.getByPlaceholderText(/one perfume name per line/i), {
    target: { value: "Aventus\nSauvage" },
  });
  fireEvent.click(screen.getByText(/look up all/i));
  await waitFor(() => expect(screen.getByText("Sauvage")).toBeInTheDocument());

  // Drop the first result.
  fireEvent.click(screen.getAllByRole("checkbox")[0]);
  fireEvent.click(screen.getByText(/save 1 selected/i));

  await waitFor(() =>
    expect(screen.getByText(/added 1 perfume/i)).toBeInTheDocument(),
  );
  expect(create).toHaveBeenCalledTimes(1);
});

it("shows failed lookups in error state and does not save them", async () => {
  vi.spyOn(api, "lookupPerfume").mockImplementation(async (n: string) => {
    if (n === "Bogus") throw new Error("Lookup failed: not found");
    return draftFor(n);
  });
  const create = vi.spyOn(api, "createPerfume").mockResolvedValue({} as any);
  render(
    <MemoryRouter>
      <BatchAdd />
    </MemoryRouter>,
  );

  fireEvent.change(screen.getByPlaceholderText(/one perfume name per line/i), {
    target: { value: "Aventus\nBogus" },
  });
  fireEvent.click(screen.getByText(/look up all/i));

  await waitFor(() =>
    expect(screen.getByText(/not found/i)).toBeInTheDocument(),
  );
  // Only the successful row is selectable → "Save 1 selected".
  fireEvent.click(screen.getByText(/save 1 selected/i));
  await waitFor(() => expect(create).toHaveBeenCalledTimes(1));
});

it("flags duplicates found in the collection", async () => {
  vi.spyOn(api, "lookupPerfume").mockImplementation(async (n: string) =>
    draftFor(n),
  );
  vi.spyOn(api, "checkDuplicate").mockResolvedValue({ duplicate: true, id: 1 });
  render(
    <MemoryRouter>
      <BatchAdd />
    </MemoryRouter>,
  );

  fireEvent.change(screen.getByPlaceholderText(/one perfume name per line/i), {
    target: { value: "Aventus" },
  });
  fireEvent.click(screen.getByText(/look up all/i));

  await waitFor(() =>
    expect(screen.getByText(/already in collection/i)).toBeInTheDocument(),
  );
});
