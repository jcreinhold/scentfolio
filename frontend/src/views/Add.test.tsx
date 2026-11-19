import {
  act,
  render,
  screen,
  waitFor,
  fireEvent,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi, it, expect } from "vitest";
import Add from "./Add";
import * as api from "../api";
import type { Draft, Perfume } from "../types";

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

it("saves to the chosen section only once while the request is pending", async () => {
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
    .mockReturnValue(Promise.withResolvers<Perfume>().promise);

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
  const save = await screen.findByRole("button", { name: "Save to Saved" });
  fireEvent.click(save);
  expect(save).toBeDisabled();
  fireEvent.click(save);
  expect(create).toHaveBeenCalledTimes(1);
  expect(create).toHaveBeenCalledWith(
    expect.objectContaining({ status: "saved" }),
  );
});

it("removes the previous draft as soon as a new lookup starts", async () => {
  const next = Promise.withResolvers<Draft>();
  vi.spyOn(api, "lookupPerfume")
    .mockResolvedValueOnce({
      confidence: "low",
      perfume: {
        name: "First draft",
        status: "collection",
        house: "",
        perfumer: null,
        year: null,
        scent_families: [],
        description: "",
        my_impressions: "",
        formats: [],
        source_urls: [],
        notes: [],
      },
    })
    .mockReturnValueOnce(next.promise);
  vi.spyOn(api, "checkDuplicate").mockResolvedValue({
    duplicate: false,
    id: null,
  });
  render(
    <MemoryRouter>
      <Add />
    </MemoryRouter>,
  );
  const search = screen.getByPlaceholderText(/perfume by name/i);
  fireEvent.change(search, { target: { value: "First" } });
  fireEvent.click(screen.getByRole("button", { name: "Look up" }));
  await screen.findByDisplayValue("First draft");
  fireEvent.change(search, { target: { value: "Second" } });
  fireEvent.click(screen.getByRole("button", { name: "Look up" }));
  expect(screen.queryByDisplayValue("First draft")).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Save to collection" }),
  ).not.toBeInTheDocument();
  next.reject(new Error("Try again in a moment."));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Try again in a moment.",
  );
});

it("locks the add mode and stops queued batch lookups when leaving the page", async () => {
  const pending = Promise.withResolvers<Draft>();
  const lookup = vi
    .spyOn(api, "lookupPerfume")
    .mockReturnValue(pending.promise);
  const { unmount } = render(
    <MemoryRouter>
      <Add />
    </MemoryRouter>,
  );

  fireEvent.click(screen.getByRole("tab", { name: "Batch add" }));
  fireEvent.change(screen.getByPlaceholderText(/one perfume name per line/i), {
    target: { value: "A\nB\nC\nD\nE" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Look up all (5)" }));
  expect(screen.getByRole("tab", { name: "One at a time" })).toBeDisabled();
  expect(lookup).toHaveBeenCalledTimes(4);

  unmount();
  expect(lookup.mock.calls.every(([, signal]) => signal?.aborted)).toBe(true);
  await act(async () => pending.reject(new Error("Canceled")));
  expect(lookup).toHaveBeenCalledTimes(4);
});
