import { describe, it, expect, beforeEach } from "vitest";
import { updateFavicon } from "../../src/application/services/favicon-service.js";

describe("FaviconService", () => {
  beforeEach(() => {
    // Remove any existing favicon link from previous tests
    document.querySelector('link[rel="icon"]')?.remove();
  });

  it("should create favicon link with acronym and hash-based color when none exists", () => {
    updateFavicon("My MVG Departures");

    const link = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
    expect(link).not.toBeNull();
    expect(link?.href).toMatch(/^data:image\/svg\+xml,/);
    expect(link?.href).toContain("MMD"); // Acronym from first 3 words
    // Hex color is URL-encoded in data URL (%23 = #)
    expect(decodeURIComponent(link?.href ?? "")).toMatch(/#[0-9a-f]{6}/i);
  });

  it("should update existing favicon when title changes", () => {
    updateFavicon("Home");
    const firstHref =
      document.querySelector<HTMLLinkElement>('link[rel="icon"]')?.href;

    updateFavicon("Work Commute");
    const secondHref =
      document.querySelector<HTMLLinkElement>('link[rel="icon"]')?.href;

    expect(firstHref).toContain("H");
    expect(secondHref).toContain("WC");
    expect(firstHref).not.toBe(secondHref);
  });

  it("should produce same color for same title (deterministic)", () => {
    updateFavicon("Test Route");
    const href1 =
      document.querySelector<HTMLLinkElement>('link[rel="icon"]')?.href;

    document.querySelector('link[rel="icon"]')?.remove();
    updateFavicon("Test Route");
    const href2 =
      document.querySelector<HTMLLinkElement>('link[rel="icon"]')?.href;

    expect(href1).toBe(href2);
  });
});
