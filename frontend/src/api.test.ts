import { it, expect, vi, beforeEach } from "vitest";
import { listPerfumes, lookupPerfume } from "./api";

beforeEach(() => {
  global.fetch = vi.fn();
});

it("listPerfumes builds query string from filters", async () => {
  (global.fetch as any).mockResolvedValue({ ok: true, json: async () => [] });
  await listPerfumes({ q: "bergamot", family: "Fresh" });
  const url = (global.fetch as any).mock.calls[0][0];
  expect(url).toContain("q=bergamot");
  expect(url).toContain("family=Fresh");
});

it("lookupPerfume posts the name", async () => {
  (global.fetch as any).mockResolvedValue({
    ok: true,
    json: async () => ({ confidence: "high" }),
  });
  const d = await lookupPerfume("Aventus");
  expect(d.confidence).toBe("high");
});
