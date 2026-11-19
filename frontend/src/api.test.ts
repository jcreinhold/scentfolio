import { it, expect, vi, beforeEach } from "vitest";
import { getNote, listPerfumes, lookupPerfume } from "./api";

beforeEach(() => {
  global.fetch = vi.fn();
});

it("builds the page query and reads the matching total", async () => {
  vi.mocked(fetch).mockResolvedValue(
    Response.json([], { headers: { "X-Total-Count": "83" } }),
  );
  const signal = new AbortController().signal;
  const result = await listPerfumes(
    {
      q: "bergamot",
      family: "Fresh",
      status: "saved",
      limit: 40,
      offset: 40,
      sort: { key: "notes", direction: "desc" },
    },
    signal,
  );
  const [url, options] = vi.mocked(fetch).mock.calls[0];
  expect(
    Object.fromEntries(new URL(String(url), "https://test").searchParams),
  ).toEqual({
    q: "bergamot",
    family: "Fresh",
    status: "saved",
    limit: "40",
    offset: "40",
    sort: "notes",
    direction: "desc",
  });
  expect(options?.signal).toBe(signal);
  expect(result).toEqual({ perfumes: [], total: 83 });
});

it("lookupPerfume posts the name", async () => {
  vi.mocked(fetch).mockResolvedValue(Response.json({ confidence: "high" }));
  const draft = await lookupPerfume("Aventus");
  expect(draft.confidence).toBe("high");
  expect(fetch).toHaveBeenCalledWith(
    "/api/lookup",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ name: "Aventus" }),
    }),
  );
});

it("shows the backend detail for a retryable provider error", async () => {
  vi.mocked(fetch).mockResolvedValue(
    Response.json({ detail: "Try again in a moment." }, { status: 503 }),
  );
  await expect(lookupPerfume("Aventus")).rejects.toThrow(
    "Try again in a moment.",
  );
});

it("reports the HTTP status when an error has no JSON body", async () => {
  vi.mocked(fetch).mockResolvedValue(
    new Response("Not found", { status: 404 }),
  );
  await expect(getNote("unknown")).rejects.toThrow("Request failed (404)");
});
