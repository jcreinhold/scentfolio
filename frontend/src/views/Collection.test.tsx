import {
  act,
  render,
  screen,
  waitFor,
  fireEvent,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { it, expect, vi, beforeEach } from "vitest";
import Collection from "./Collection";
import * as api from "../api";
import type { Perfume } from "../types";

// The view toggle persists to localStorage; isolate each test so the default
// (card view) is deterministic regardless of order.
beforeEach(() => localStorage.clear());

const sauvage: Perfume = {
  id: 1,
  name: "Sauvage",
  status: "collection",
  house: "Dior",
  perfumer: null,
  year: 2015,
  scent_families: ["Fresh"],
  description: "",
  my_impressions: "",
  formats: ["full"],
  source_urls: [],
  notes: [{ id: 1, name: "bergamot", tier: "top" }],
};

function page(perfumes: Perfume[], total = perfumes.length) {
  return { perfumes, total };
}

it("renders perfume cards from the API", async () => {
  vi.spyOn(api, "listPerfumes").mockResolvedValue(page([sauvage]));
  render(
    <MemoryRouter>
      <Collection />
    </MemoryRouter>,
  );
  await waitFor(() => expect(screen.getByText("Sauvage")).toBeInTheDocument());
  expect(screen.getByText("bergamot")).toBeInTheDocument();
});

it("removes a perfume from the grid when its ✕ is confirmed", async () => {
  vi.spyOn(api, "listPerfumes")
    .mockResolvedValueOnce(page([sauvage]))
    .mockResolvedValue(page([]));
  const del = vi.spyOn(api, "deletePerfume").mockResolvedValue(undefined);
  vi.spyOn(window, "confirm").mockReturnValue(true);
  render(
    <MemoryRouter>
      <Collection />
    </MemoryRouter>,
  );
  await waitFor(() => expect(screen.getByText("Sauvage")).toBeInTheDocument());
  fireEvent.click(screen.getByLabelText("Remove Sauvage"));
  await waitFor(() => expect(del).toHaveBeenCalledWith(1));
  await waitFor(() =>
    expect(screen.queryByText("Sauvage")).not.toBeInTheDocument(),
  );
});

it("offers a CSV export link scoped to the section", async () => {
  vi.spyOn(api, "listPerfumes").mockResolvedValue(
    page([{ ...sauvage, status: "saved" }]),
  );
  render(
    <MemoryRouter>
      <Collection status="saved" />
    </MemoryRouter>,
  );
  await waitFor(() => expect(screen.getByText("Sauvage")).toBeInTheDocument());
  expect(screen.getByRole("link", { name: /export csv/i })).toHaveAttribute(
    "href",
    "/api/perfumes/export.csv?status=saved",
  );
});

it("renders the Saved section and requests that status", async () => {
  const list = vi.spyOn(api, "listPerfumes").mockResolvedValue(page([]));
  render(
    <MemoryRouter>
      <Collection status="saved" />
    </MemoryRouter>,
  );
  await waitFor(() =>
    expect(screen.getByText(/fragrances you're tracking/i)).toBeInTheDocument(),
  );
  expect(screen.getByText(/nothing saved yet/i)).toBeInTheDocument();
  expect(list).toHaveBeenCalledWith(
    expect.objectContaining({ status: "saved" }),
    expect.any(AbortSignal),
  );
});

it("switches to the sortable table view via the toggle", async () => {
  vi.spyOn(api, "listPerfumes").mockResolvedValue(page([sauvage]));
  render(
    <MemoryRouter>
      <Collection />
    </MemoryRouter>,
  );
  await waitFor(() => expect(screen.getByText("Sauvage")).toBeInTheDocument());

  fireEvent.click(screen.getByRole("tab", { name: "Table" }));
  // A sortable column header (unique to the table view) is now present.
  expect(
    await screen.findByRole("button", { name: /house/i }),
  ).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Sauvage" })).toHaveAttribute(
    "href",
    "/perfume/1",
  );
});

it("toggles a size on a card and persists it", async () => {
  const withTravel = { ...sauvage, formats: ["full", "travel"] };
  vi.spyOn(api, "listPerfumes")
    .mockResolvedValueOnce(page([sauvage]))
    .mockResolvedValueOnce(page([withTravel]))
    .mockResolvedValue(page([{ ...sauvage, formats: ["travel"] }]));
  const upd = vi.spyOn(api, "updatePerfume").mockResolvedValue(withTravel);
  render(
    <MemoryRouter>
      <Collection />
    </MemoryRouter>,
  );
  await waitFor(() => expect(screen.getByText("Sauvage")).toBeInTheDocument());

  // sauvage starts with "full"; adding "travel" should persist ["full","travel"].
  fireEvent.click(screen.getByLabelText("Add Travel size for Sauvage"));
  await waitFor(() =>
    expect(upd).toHaveBeenCalledWith(1, { formats: ["full", "travel"] }),
  );

  // A confirmed update preserves "full"; removing it leaves ["travel"].
  fireEvent.click(await screen.findByLabelText("Remove Full size for Sauvage"));
  await waitFor(() =>
    expect(upd).toHaveBeenCalledWith(1, { formats: ["travel"] }),
  );
});

it("does not delete when the confirm is dismissed", async () => {
  vi.spyOn(api, "listPerfumes").mockResolvedValue(page([sauvage]));
  const del = vi.spyOn(api, "deletePerfume").mockResolvedValue(undefined);
  vi.spyOn(window, "confirm").mockReturnValue(false);
  render(
    <MemoryRouter>
      <Collection />
    </MemoryRouter>,
  );
  await waitFor(() => expect(screen.getByText("Sauvage")).toBeInTheDocument());
  fireEvent.click(screen.getByLabelText("Remove Sauvage"));
  expect(del).not.toHaveBeenCalled();
});

it("discards a filter result that finishes after a newer request", async () => {
  const old = Promise.withResolvers<api.PerfumePage>();
  const recent = Promise.withResolvers<api.PerfumePage>();
  const list = vi.spyOn(api, "listPerfumes").mockImplementation(({ q }) => {
    if (q === "old") return old.promise;
    if (q === "new") return recent.promise;
    return Promise.resolve(page([sauvage]));
  });
  render(
    <MemoryRouter>
      <Collection />
    </MemoryRouter>,
  );
  await screen.findByText("Sauvage");
  const search = screen.getByPlaceholderText("Search names or notes…");
  fireEvent.change(search, { target: { value: "old" } });
  fireEvent.change(search, { target: { value: "new" } });
  expect(list.mock.calls[1][1]?.aborted).toBe(true);
  await act(async () =>
    recent.resolve(page([{ ...sauvage, name: "New result" }])),
  );
  await act(async () =>
    old.resolve(page([{ ...sauvage, name: "Old result" }])),
  );
  expect(screen.getByText("New result")).toBeInTheDocument();
  expect(screen.queryByText("Old result")).not.toBeInTheDocument();
});

it("preserves a successful deletion when another card update fails", async () => {
  const second = { ...sauvage, id: 2, name: "Aventus" };
  const update = Promise.withResolvers<Perfume>();
  vi.spyOn(api, "listPerfumes")
    .mockResolvedValueOnce(page([sauvage, second]))
    .mockResolvedValue(page([sauvage]));
  vi.spyOn(api, "updatePerfume").mockReturnValue(update.promise);
  vi.spyOn(api, "deletePerfume").mockResolvedValue(undefined);
  vi.spyOn(window, "confirm").mockReturnValue(true);

  render(
    <MemoryRouter>
      <Collection />
    </MemoryRouter>,
  );
  await screen.findByText("Aventus");
  fireEvent.click(screen.getByLabelText("Add Travel size for Sauvage"));
  fireEvent.click(screen.getByLabelText("Remove Aventus"));
  await screen.findByText("Sauvage");
  expect(screen.queryByText("Aventus")).not.toBeInTheDocument();
  await act(async () => update.reject(new Error("Update failed")));
  expect(screen.getByRole("alert")).toHaveTextContent("Update failed");
  expect(screen.queryByText("Aventus")).not.toBeInTheDocument();
});

it("requests pages and resets the offset when filters or table sort change", async () => {
  const list = vi
    .spyOn(api, "listPerfumes")
    .mockImplementation(async ({ offset }) =>
      page([{ ...sauvage, name: offset ? "Later scent" : "First scent" }], 81),
    );
  render(
    <MemoryRouter>
      <Collection />
    </MemoryRouter>,
  );
  await screen.findByText("First scent");
  expect(screen.getByText(/81 scents/)).toBeInTheDocument();
  expect(list.mock.lastCall?.[0]).toMatchObject({
    limit: 40,
    offset: 0,
    sort: undefined,
  });
  fireEvent.click(screen.getByRole("button", { name: "Next" }));
  await screen.findByText("Later scent");
  expect(list.mock.lastCall?.[0].offset).toBe(40);
  fireEvent.change(screen.getByLabelText("Filter by family"), {
    target: { value: "Fresh" },
  });
  await screen.findByText("First scent");
  expect(list.mock.lastCall?.[0]).toMatchObject({ offset: 0, family: "Fresh" });
  fireEvent.click(screen.getByRole("tab", { name: "Table" }));
  await screen.findByRole("columnheader", { name: "Name" });
  expect(list.mock.lastCall?.[0].sort).toEqual({
    key: "name",
    direction: "asc",
  });
  fireEvent.click(screen.getByRole("button", { name: "Next" }));
  await screen.findByText("Later scent");
  fireEvent.click(screen.getByRole("button", { name: "Year" }));
  await screen.findByText("First scent");
  expect(list.mock.lastCall?.[0]).toMatchObject({
    offset: 0,
    sort: { key: "year", direction: "asc" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Year" }));
  await screen.findByText("First scent");
  expect(list.mock.lastCall?.[0].sort).toEqual({
    key: "year",
    direction: "desc",
  });
});

it("returns to the last populated page after deleting its final row", async () => {
  let total = 41;
  vi.spyOn(api, "listPerfumes").mockImplementation(async ({ offset }) => {
    if (offset === 0) return page([sauvage], total);
    return page(
      total > 40 ? [{ ...sauvage, id: 2, name: "Last scent" }] : [],
      total,
    );
  });
  vi.spyOn(api, "deletePerfume").mockImplementation(async () => {
    total = 40;
  });
  vi.spyOn(window, "confirm").mockReturnValue(true);

  render(
    <MemoryRouter>
      <Collection />
    </MemoryRouter>,
  );
  fireEvent.click(await screen.findByRole("button", { name: "Next" }));
  fireEvent.click(await screen.findByLabelText("Remove Last scent"));
  await screen.findByText("Sauvage");
  expect(screen.queryByText("Nothing matches")).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Next" }),
  ).not.toBeInTheDocument();
});
