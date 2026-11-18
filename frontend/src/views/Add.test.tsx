import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi, it, expect } from "vitest";
import Add from "./Add";
import * as api from "../api";

it("looks up a name and shows the draft for confirmation", async () => {
  const sourceUrl = "https://example.test/aventus";
  vi.spyOn(api, "lookupPerfume").mockResolvedValue({
    confidence: "high",
    perfume: {
      name: "Aventus",
      house: "Creed",
      perfumer: "Olivier Creed",
      year: 2010,
      scent_families: ["Chypre"],
      description: "Smoky.",
      my_impressions: "",
      formats: [],
      source_urls: [
        sourceUrl,
        "file:///aventus",
        "no-url",
        "HTTPS://EXAMPLE.TEST/aventus",
      ],
      notes: [{ id: 0, name: "bergamot", tier: "top" }],
    },
  } as any);
  vi.spyOn(api, "checkDuplicate").mockResolvedValue({
    duplicate: false,
    id: null,
  });

  render(
    <MemoryRouter>
      <Add />
    </MemoryRouter>,
  );
  fireEvent.change(screen.getByPlaceholderText(/perfume by name/i), {
    target: { value: "Aventus" },
  });
  fireEvent.click(screen.getByText(/look up/i));

  await waitFor(() =>
    expect(screen.getByDisplayValue("Aventus")).toBeInTheDocument(),
  );
  expect(screen.getByText(/high confidence/i)).toBeInTheDocument();
  expect(screen.getByText("bergamot")).toBeInTheDocument();
  const source = screen.getByRole("link", { name: sourceUrl });
  expect(source).toHaveAttribute("href", sourceUrl);
  expect(source).toHaveAttribute("target", "_blank");
  expect(screen.getAllByRole("link")).toHaveLength(1);
});

it("warns when the looked-up perfume is already in the collection", async () => {
  vi.spyOn(api, "lookupPerfume").mockResolvedValue({
    confidence: "medium",
    perfume: {
      name: "Aventus",
      house: "Creed",
      perfumer: null,
      year: null,
      scent_families: ["Chypre"],
      description: "",
      my_impressions: "",
      formats: [],
      source_urls: [],
      notes: [],
    },
  } as any);
  vi.spyOn(api, "checkDuplicate").mockResolvedValue({ duplicate: true, id: 1 });
  render(
    <MemoryRouter>
      <Add />
    </MemoryRouter>,
  );
  fireEvent.change(screen.getByPlaceholderText(/perfume by name/i), {
    target: { value: "Aventus" },
  });
  fireEvent.click(screen.getByText(/look up/i));
  await waitFor(() =>
    expect(screen.getByText(/already have a perfume/i)).toBeInTheDocument(),
  );
  expect(
    screen.queryByRole("group", { name: "Sources" }),
  ).not.toBeInTheDocument();
});

it("saves to the Saved section when that destination is chosen", async () => {
  vi.spyOn(api, "lookupPerfume").mockResolvedValue({
    confidence: "high",
    perfume: {
      name: "Aventus",
      house: "Creed",
      perfumer: null,
      year: null,
      scent_families: ["Chypre"],
      description: "",
      my_impressions: "",
      formats: [],
      source_urls: [],
      notes: [],
    },
  } as any);
  vi.spyOn(api, "checkDuplicate").mockResolvedValue({
    duplicate: false,
    id: null,
  });
  const create = vi
    .spyOn(api, "createPerfume")
    .mockResolvedValue({ id: 9 } as any);

  render(
    <MemoryRouter>
      <Add />
    </MemoryRouter>,
  );
  fireEvent.click(screen.getByRole("tab", { name: "Saved" })); // destination toggle
  fireEvent.change(screen.getByPlaceholderText(/perfume by name/i), {
    target: { value: "Aventus" },
  });
  fireEvent.click(screen.getByText(/look up/i));
  await waitFor(() =>
    expect(screen.getByDisplayValue("Aventus")).toBeInTheDocument(),
  );
  fireEvent.click(screen.getByText(/save to saved/i));
  await waitFor(() =>
    expect(create).toHaveBeenCalledWith(
      expect.objectContaining({ status: "saved" }),
    ),
  );
});
