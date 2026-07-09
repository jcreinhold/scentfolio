import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { it, expect, vi } from "vitest";
import Collection from "./Collection";
import * as api from "../api";

const sauvage = {
  id: 1, name: "Sauvage", house: "Dior", perfumer: null, year: 2015,
  scent_family: "Fresh", description: "", my_impressions: "",
  formats: ["full"], source_urls: [], notes: [{ id: 1, name: "bergamot", tier: "top" }],
};

it("renders perfume cards from the API", async () => {
  vi.spyOn(api, "listPerfumes").mockResolvedValue([sauvage as any]);
  render(<MemoryRouter><Collection /></MemoryRouter>);
  await waitFor(() => expect(screen.getByText("Sauvage")).toBeInTheDocument());
  expect(screen.getByText("bergamot")).toBeInTheDocument();
});

it("removes a perfume from the grid when its ✕ is confirmed", async () => {
  vi.spyOn(api, "listPerfumes").mockResolvedValue([sauvage as any]);
  const del = vi.spyOn(api, "deletePerfume").mockResolvedValue(undefined);
  vi.spyOn(window, "confirm").mockReturnValue(true);
  render(<MemoryRouter><Collection /></MemoryRouter>);
  await waitFor(() => expect(screen.getByText("Sauvage")).toBeInTheDocument());
  fireEvent.click(screen.getByLabelText("Remove Sauvage"));
  await waitFor(() => expect(del).toHaveBeenCalledWith(1));
  await waitFor(() => expect(screen.queryByText("Sauvage")).not.toBeInTheDocument());
});

it("toggles a size on a card and persists it", async () => {
  vi.spyOn(api, "listPerfumes").mockResolvedValue([sauvage as any]);
  const upd = vi.spyOn(api, "updatePerfume").mockResolvedValue({ ...sauvage, formats: ["full", "travel"] } as any);
  render(<MemoryRouter><Collection /></MemoryRouter>);
  await waitFor(() => expect(screen.getByText("Sauvage")).toBeInTheDocument());

  // sauvage starts with "full"; adding "travel" should persist ["full","travel"].
  fireEvent.click(screen.getByLabelText("Add Travel size for Sauvage"));
  await waitFor(() => expect(upd).toHaveBeenCalledWith(1, { formats: ["full", "travel"] }));

  // "full" is still active after the optimistic add; removing it leaves ["travel"].
  fireEvent.click(screen.getByLabelText("Remove Full size for Sauvage"));
  await waitFor(() => expect(upd).toHaveBeenCalledWith(1, { formats: ["travel"] }));
});

it("does not delete when the confirm is dismissed", async () => {
  vi.spyOn(api, "listPerfumes").mockResolvedValue([sauvage as any]);
  const del = vi.spyOn(api, "deletePerfume").mockResolvedValue(undefined);
  vi.spyOn(window, "confirm").mockReturnValue(false);
  render(<MemoryRouter><Collection /></MemoryRouter>);
  await waitFor(() => expect(screen.getByText("Sauvage")).toBeInTheDocument());
  fireEvent.click(screen.getByLabelText("Remove Sauvage"));
  expect(del).not.toHaveBeenCalled();
});
