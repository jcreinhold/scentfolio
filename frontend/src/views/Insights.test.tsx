import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { vi, it, expect } from "vitest";
import Insights from "./Insights";
import * as api from "../api";

it("renders note frequency, families, and similar pairs", async () => {
  vi.spyOn(api, "insightNotes").mockResolvedValue({
    top: [{ note: "bergamot", count: 2 }],
    heart: [{ note: "rose", count: 1 }],
    base: [],
  });
  vi.spyOn(api, "insightFamilies").mockResolvedValue([
    { family: "Fresh", count: 1 },
  ]);
  vi.spyOn(api, "insightSimilar").mockResolvedValue([
    {
      a: "Sauvage",
      b: "Aventus",
      score: 0.62,
      shared_families: ["Woody"],
      shared_top: ["bergamot"],
      shared_heart: [],
      shared_base: [],
    },
  ]);
  render(<Insights />);
  await waitFor(() =>
    expect(screen.getByText(/most common top notes/i)).toBeInTheDocument(),
  );
  expect(screen.getByText(/most common heart notes/i)).toBeInTheDocument();
  expect(screen.getByText(/most common base notes/i)).toBeInTheDocument();
  expect(screen.getByText(/Sauvage/)).toBeInTheDocument();
  expect(screen.getByText(/Aventus/)).toBeInTheDocument();
  expect(screen.getByText("62% match")).toBeInTheDocument();
});

it("refreshes both family-dependent results and shows a partial failure", async () => {
  vi.spyOn(api, "insightNotes").mockResolvedValue({
    top: [],
    heart: [],
    base: [],
  });
  const pair = {
    a: "Sauvage",
    b: "Aventus",
    score: 0.25,
    shared_families: [],
    shared_top: [],
    shared_heart: [],
    shared_base: [],
  };
  vi.spyOn(api, "insightSimilar")
    .mockResolvedValueOnce([pair])
    .mockResolvedValueOnce([{ ...pair, score: 0.75 }]);
  const fam = vi
    .spyOn(api, "insightFamilies")
    .mockResolvedValueOnce([{ family: "Woody", count: 1 }]) // initial
    .mockResolvedValueOnce([{ family: "Gourmand", count: 1 }]); // after reclassify
  const rc = vi
    .spyOn(api, "reclassifyPerfumes")
    .mockResolvedValue({ updated: 1, failed: 1 });

  render(<Insights />);
  await screen.findByText("25% match");
  fireEvent.click(screen.getByText(/re-classify families/i));
  await waitFor(() => expect(rc).toHaveBeenCalledTimes(1));
  await waitFor(() => expect(fam).toHaveBeenCalledTimes(2));
  expect(await screen.findByText("75% match")).toBeInTheDocument();
  expect(screen.queryByText("25% match")).not.toBeInTheDocument();
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Could not reclassify 1 perfume.",
  );
});
