import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi } from "vitest";
import Collection from "./Collection";
import * as api from "../api";

it("renders perfume cards from the API", async () => {
  vi.spyOn(api, "listPerfumes").mockResolvedValue([{
    id: 1, name: "Sauvage", house: "Dior", perfumer: null, year: 2015,
    scent_family: "Fresh", description: "", my_impressions: "",
    formats: ["full"], source_urls: [], notes: [{ id: 1, name: "bergamot", tier: "top" }],
  }]);
  render(<MemoryRouter><Collection /></MemoryRouter>);
  await waitFor(() => expect(screen.getByText("Sauvage")).toBeInTheDocument());
  expect(screen.getByText("bergamot")).toBeInTheDocument();
});
