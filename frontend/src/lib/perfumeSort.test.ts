import { describe, it, expect } from "vitest";
import { sortPerfumes } from "./perfumeSort";
import type { Perfume } from "../types";

function p(over: Partial<Perfume>): Perfume {
  return {
    id: 0,
    name: "x",
    status: "collection",
    house: "h",
    perfumer: null,
    year: null,
    scent_families: [],
    description: "",
    my_impressions: "",
    formats: [],
    source_urls: [],
    notes: [],
    ...over,
  };
}

const names = (ps: Perfume[]) => ps.map((x) => x.name);

describe("sortPerfumes", () => {
  it("sorts by name ascending and descending", () => {
    const list = [
      p({ name: "Sauvage" }),
      p({ name: "Aventus" }),
      p({ name: "Rose 31" }),
    ];
    expect(names(sortPerfumes(list, "name", "asc"))).toEqual([
      "Aventus",
      "Rose 31",
      "Sauvage",
    ]);
    expect(names(sortPerfumes(list, "name", "desc"))).toEqual([
      "Sauvage",
      "Rose 31",
      "Aventus",
    ]);
  });

  it("sorts by note count", () => {
    const list = [
      p({ name: "few", notes: [{ id: 1, name: "a" }] }),
      p({
        name: "many",
        notes: [
          { id: 1, name: "a" },
          { id: 2, name: "b" },
          { id: 3, name: "c" },
        ],
      }),
      p({
        name: "some",
        notes: [
          { id: 1, name: "a" },
          { id: 2, name: "b" },
        ],
      }),
    ];
    expect(names(sortPerfumes(list, "notes", "asc"))).toEqual([
      "few",
      "some",
      "many",
    ]);
  });

  it("keeps missing values (null year) last in BOTH directions", () => {
    const list = [
      p({ name: "undated" }),
      p({ name: "y2000", year: 2000 }),
      p({ name: "y2015", year: 2015 }),
    ];
    expect(names(sortPerfumes(list, "year", "asc"))).toEqual([
      "y2000",
      "y2015",
      "undated",
    ]);
    expect(names(sortPerfumes(list, "year", "desc"))).toEqual([
      "y2015",
      "y2000",
      "undated",
    ]);
  });

  it("sorts by perfumer collection frequency, grouping same perfumer together", () => {
    const list = [
      p({ name: "a1", perfumer: "Alberto Morillas" }),
      p({ name: "solo", perfumer: "Solo Nose" }),
      p({ name: "a2", perfumer: "Alberto Morillas" }),
      p({ name: "none", perfumer: null }),
    ];
    // desc: the perfumer with the most perfumes (Morillas ×2) leads; the two
    // Morillas rows stay adjacent; the perfumer-less one sinks last.
    const out = names(sortPerfumes(list, "perfumer", "desc"));
    expect(out.slice(0, 2).sort()).toEqual(["a1", "a2"]);
    expect(out[2]).toBe("solo");
    expect(out[3]).toBe("none"); // missing perfumer always last
  });

  it("keeps perfumes with no perfumer last even ascending", () => {
    const list = [
      p({ name: "none", perfumer: null }),
      p({ name: "has", perfumer: "X" }),
    ];
    expect(names(sortPerfumes(list, "perfumer", "asc"))).toEqual([
      "has",
      "none",
    ]);
  });

  it("does not mutate the input array", () => {
    const list = [p({ name: "b" }), p({ name: "a" })];
    const before = names(list);
    sortPerfumes(list, "name", "asc");
    expect(names(list)).toEqual(before);
  });
});
