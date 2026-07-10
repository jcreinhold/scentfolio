import { describe, it, expect } from "vitest";
import { sortPerfumes } from "./perfumeSort";
import type { Perfume } from "../types";

function p(over: Partial<Perfume>): Perfume {
  return {
    id: 0, name: "x", house: "h", perfumer: null, year: null,
    scent_family: null, description: "", my_impressions: "",
    formats: [], source_urls: [], notes: [], ...over,
  };
}

const names = (ps: Perfume[]) => ps.map((x) => x.name);

describe("sortPerfumes", () => {
  it("sorts by name ascending and descending", () => {
    const list = [p({ name: "Sauvage" }), p({ name: "Aventus" }), p({ name: "Rose 31" })];
    expect(names(sortPerfumes(list, "name", "asc"))).toEqual(["Aventus", "Rose 31", "Sauvage"]);
    expect(names(sortPerfumes(list, "name", "desc"))).toEqual(["Sauvage", "Rose 31", "Aventus"]);
  });

  it("sorts by note count", () => {
    const list = [
      p({ name: "few", notes: [{ id: 1, name: "a" }] }),
      p({ name: "many", notes: [{ id: 1, name: "a" }, { id: 2, name: "b" }, { id: 3, name: "c" }] }),
      p({ name: "some", notes: [{ id: 1, name: "a" }, { id: 2, name: "b" }] }),
    ];
    expect(names(sortPerfumes(list, "notes", "asc"))).toEqual(["few", "some", "many"]);
  });

  it("keeps missing values (null year) last in BOTH directions", () => {
    const list = [p({ name: "undated" }), p({ name: "y2000", year: 2000 }), p({ name: "y2015", year: 2015 })];
    expect(names(sortPerfumes(list, "year", "asc"))).toEqual(["y2000", "y2015", "undated"]);
    expect(names(sortPerfumes(list, "year", "desc"))).toEqual(["y2015", "y2000", "undated"]);
  });

  it("does not mutate the input array", () => {
    const list = [p({ name: "b" }), p({ name: "a" })];
    const before = names(list);
    sortPerfumes(list, "name", "asc");
    expect(names(list)).toEqual(before);
  });
});
