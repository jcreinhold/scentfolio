import { describe, it, expect, vi, beforeEach } from "vitest";
import { listPerfumes, lookupPerfume, mapPool } from "./api";

beforeEach(() => {
  global.fetch = vi.fn();
});

describe("mapPool", () => {
  it("preserves input order and reports each outcome", async () => {
    const out = await mapPool([1, 2, 3], 2, async (n) => n * 10);
    expect(out).toEqual([
      { ok: true, value: 10 }, { ok: true, value: 20 }, { ok: true, value: 30 },
    ]);
  });

  it("isolates a single rejection without sinking the batch", async () => {
    const out = await mapPool([1, 2, 3], 2, async (n) => {
      if (n === 2) throw new Error("boom");
      return n;
    });
    expect(out[0]).toEqual({ ok: true, value: 1 });
    expect(out[1].ok).toBe(false);
    expect(out[2]).toEqual({ ok: true, value: 3 });
  });

  it("never exceeds the concurrency limit", async () => {
    let inFlight = 0, peak = 0;
    await mapPool([1, 2, 3, 4, 5, 6], 2, async () => {
      inFlight++; peak = Math.max(peak, inFlight);
      await new Promise((r) => setTimeout(r, 5));
      inFlight--;
    });
    expect(peak).toBeLessThanOrEqual(2);
  });

  it("fires onSettle per item", async () => {
    const seen: number[] = [];
    await mapPool([1, 2, 3], 3, async (n) => n, (i) => { seen.push(i); });
    expect(seen.sort()).toEqual([0, 1, 2]);
  });
});

it("listPerfumes builds query string from filters", async () => {
  (global.fetch as any).mockResolvedValue({ ok: true, json: async () => [] });
  await listPerfumes({ q: "bergamot", family: "Fresh" });
  const url = (global.fetch as any).mock.calls[0][0];
  expect(url).toContain("q=bergamot");
  expect(url).toContain("family=Fresh");
});

it("lookupPerfume posts the name", async () => {
  (global.fetch as any).mockResolvedValue({ ok: true, json: async () => ({ confidence: "high" }) });
  const d = await lookupPerfume("Aventus");
  expect(d.confidence).toBe("high");
});
