import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { vi, it, expect } from "vitest";
import Insights from "./Insights";
import * as api from "../api";

it("renders note frequency, families, and similar pairs", async () => {
  vi.spyOn(api, "insightNotes").mockResolvedValue([{ note: "bergamot", count: 2 }]);
  vi.spyOn(api, "insightFamilies").mockResolvedValue([{ family: "Fresh", count: 1 }]);
  vi.spyOn(api, "insightSimilar").mockResolvedValue([{ a: "Sauvage", b: "Aventus", score: 0.62,
    shared_families: ["Woody"], shared_top: ["bergamot"], shared_heart: [], shared_base: [] }]);
  render(<Insights />);
  await waitFor(() => expect(screen.getByText(/Most common notes/i)).toBeInTheDocument());
  expect(screen.getByText(/Sauvage/)).toBeInTheDocument();
  expect(screen.getByText(/Aventus/)).toBeInTheDocument();
  expect(screen.getByText("62% match")).toBeInTheDocument();
});

it("re-classifies families and refreshes the breakdown", async () => {
  vi.spyOn(api, "insightNotes").mockResolvedValue([]);
  vi.spyOn(api, "insightSimilar").mockResolvedValue([]);
  const fam = vi.spyOn(api, "insightFamilies")
    .mockResolvedValueOnce([{ family: "Woody", count: 1 }])   // initial
    .mockResolvedValueOnce([{ family: "Gourmand", count: 1 }]); // after reclassify
  const rc = vi.spyOn(api, "reclassifyPerfumes").mockResolvedValue({ updated: 1 });

  render(<Insights />);
  await waitFor(() => expect(fam).toHaveBeenCalledTimes(1));
  fireEvent.click(screen.getByText(/re-classify families/i));
  await waitFor(() => expect(rc).toHaveBeenCalledTimes(1));
  await waitFor(() => expect(fam).toHaveBeenCalledTimes(2));
});
