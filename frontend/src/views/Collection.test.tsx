import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { it, expect, vi, beforeEach } from "vitest";
import Collection from "./Collection";
import * as api from "../api";

// The view toggle persists to localStorage; isolate each test so the default
// (card view) is deterministic regardless of order.
beforeEach(() => localStorage.clear());

const sauvage = {
  id: 1,
  name: "Sauvage",
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

it("renders perfume cards from the API", async () => {
  vi.spyOn(api, "listPerfumes").mockResolvedValue([sauvage as any]);
  render(
    <MemoryRouter>
      <Collection />
    </MemoryRouter>,
  );
  await waitFor(() => expect(screen.getByText("Sauvage")).toBeInTheDocument());
  expect(screen.getByText("bergamot")).toBeInTheDocument();
});

it("removes a perfume from the grid when its ✕ is confirmed", async () => {
  vi.spyOn(api, "listPerfumes").mockResolvedValue([sauvage as any]);
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
  vi.spyOn(api, "listPerfumes").mockResolvedValue([sauvage as any]);
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
  const list = vi.spyOn(api, "listPerfumes").mockResolvedValue([]);
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
  );
});

it("switches to the sortable table view via the toggle", async () => {
  vi.spyOn(api, "listPerfumes").mockResolvedValue([sauvage as any]);
  render(
    <MemoryRouter>
      <Collection />
    </MemoryRouter>,
  );
  await waitFor(() => expect(screen.getByText("Sauvage")).toBeInTheDocument());

  fireEvent.click(screen.getByRole("tab", { name: "Table" }));
  // A sortable column header (unique to the table view) is now present.
  expect(screen.getByRole("button", { name: /house/i })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Sauvage" })).toHaveAttribute(
    "href",
    "/perfume/1",
  );
});

it("toggles a size on a card and persists it", async () => {
  vi.spyOn(api, "listPerfumes").mockResolvedValue([sauvage as any]);
  const upd = vi
    .spyOn(api, "updatePerfume")
    .mockResolvedValue({ ...sauvage, formats: ["full", "travel"] } as any);
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

  // "full" is still active after the optimistic add; removing it leaves ["travel"].
  fireEvent.click(screen.getByLabelText("Remove Full size for Sauvage"));
  await waitFor(() =>
    expect(upd).toHaveBeenCalledWith(1, { formats: ["travel"] }),
  );
});

it("does not delete when the confirm is dismissed", async () => {
  vi.spyOn(api, "listPerfumes").mockResolvedValue([sauvage as any]);
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
