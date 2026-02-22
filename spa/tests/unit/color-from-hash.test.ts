import { describe, it, expect } from "vitest";
import { generatePastelColorFromText } from "../../src/utils/color-from-hash.js";

describe("color-from-hash", () => {
  it("should produce hex color for any text", () => {
    const color = generatePastelColorFromText("My MVG Departures");
    expect(color).toMatch(/^#[0-9a-f]{6}$/i);
  });

  it("should be deterministic for same input", () => {
    expect(generatePastelColorFromText("Test")).toBe(
      generatePastelColorFromText("Test"),
    );
  });

  it("should produce different colors for different text", () => {
    const a = generatePastelColorFromText("Route A");
    const b = generatePastelColorFromText("Route B");
    expect(a).not.toBe(b);
  });

  it("should respect salt parameter", () => {
    const base = generatePastelColorFromText("Title", 0.7, 0);
    const salted = generatePastelColorFromText("Title", 0.7, 1);
    expect(base).not.toBe(salted);
  });

  it("should respect brightness parameter", () => {
    const dark = generatePastelColorFromText("Title", 0.3);
    const bright = generatePastelColorFromText("Title", 0.9);
    expect(dark).not.toBe(bright);
  });
});
