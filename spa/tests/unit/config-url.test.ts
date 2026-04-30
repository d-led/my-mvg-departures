import { describe, expect, it, vi } from "vitest";
import {
  fetchConfigTomlFromSearch,
  normalizeConfigUrl,
  readConfigUrlParam,
} from "../../src/utils/config-url.js";

describe("config-url", () => {
  it("reads config URL from query string", () => {
    const value = readConfigUrlParam(
      "?foo=bar&config=https%3A%2F%2Fexample.com%2Fconfig.toml",
    );

    expect(value).toBe("https://example.com/config.toml");
  });

  it("normalizes valid http(s) URLs", () => {
    expect(normalizeConfigUrl("https://example.com/config.toml")).toBe(
      "https://example.com/config.toml",
    );
    expect(normalizeConfigUrl("http://example.com/config.toml")).toBe(
      "http://example.com/config.toml",
    );
  });

  it("rejects non-http(s) URLs", () => {
    expect(normalizeConfigUrl("file:///tmp/test.toml")).toBeNull();
    expect(normalizeConfigUrl("not-a-url")).toBeNull();
  });

  it("fetches config content when URL param is present", async () => {
    const fetchMock: typeof fetch = vi.fn(
      async () =>
        new globalThis.Response('[display]\ntitle = "Test"', {
          status: 200,
          statusText: "OK",
        }),
    ) as unknown as typeof fetch;

    const result = await fetchConfigTomlFromSearch(
      "?config=https%3A%2F%2Fexample.com%2Fconfig.toml",
      fetchMock,
    );

    expect(fetchMock).toHaveBeenCalledWith("https://example.com/config.toml");
    expect(result).toEqual({
      configUrl: "https://example.com/config.toml",
      toml: '[display]\ntitle = "Test"',
    });
  });

  it("returns null when URL param is not present", async () => {
    const fetchMock: typeof fetch = vi.fn() as unknown as typeof fetch;

    const result = await fetchConfigTomlFromSearch("?foo=bar", fetchMock);

    expect(result).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
