import { describe, it, expect } from "vitest";
import { splitPlatform } from "../../src/utils/platform-split.js";

describe("splitting the VBB platform string", () => {
  it("turns a bus stand into the same shape Munich uses", () => {
    expect(splitPlatform("Pos. 10", "Bus")).toEqual({
      platform: null,
      stopPosition: "10",
    });
  });

  it("keeps a stand label that is not a number", () => {
    expect(splitPlatform("Pos. A", "Bus")).toEqual({
      platform: null,
      stopPosition: "A",
    });
  });

  it("drops the line suffix of a U-Bahn platform", () => {
    expect(splitPlatform("2 (U9)", "U-Bahn")).toEqual({
      platform: "2",
      stopPosition: null,
    });
  });

  it("leaves a plain S-Bahn platform alone", () => {
    expect(splitPlatform("5", "S-Bahn")).toEqual({
      platform: "5",
      stopPosition: null,
    });
  });

  it("has nothing to show without a platform", () => {
    expect(splitPlatform(null, "Bus")).toEqual({
      platform: null,
      stopPosition: null,
    });
    expect(splitPlatform("", "Bus")).toEqual({
      platform: null,
      stopPosition: null,
    });
  });

  it("accepts a numeric platform", () => {
    expect(splitPlatform(3, "U-Bahn")).toEqual({
      platform: "3",
      stopPosition: null,
    });
  });
});
