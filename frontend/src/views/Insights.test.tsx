import { render, screen, waitFor } from "@testing-library/react";
import { vi, it, expect } from "vitest";
import Insights from "./Insights";
import * as api from "../api";

it("renders note frequency, families, and similar pairs", async () => {
  vi.spyOn(api, "insightNotes").mockResolvedValue([{ note: "bergamot", count: 2 }]);
  vi.spyOn(api, "insightFamilies").mockResolvedValue([{ family: "Fresh", count: 1 }]);
  vi.spyOn(api, "insightSimilar").mockResolvedValue([{ a: "Sauvage", b: "Aventus", shared: ["bergamot"], count: 1 }]);
  render(<Insights />);
  await waitFor(() => expect(screen.getByText(/Most common notes/i)).toBeInTheDocument());
  expect(screen.getByText(/Sauvage/)).toBeInTheDocument();
  expect(screen.getByText(/Aventus/)).toBeInTheDocument();
});
