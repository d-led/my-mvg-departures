import { describe, expect, it, vi } from "vitest";
import {
  fetchConfigTomlFromSearch,
  normalizeConfigUrl,
  rawConfigUrl,
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

  it("reads a GitHub file page from its raw host", () => {
    expect(
      normalizeConfigUrl(
        "https://github.com/d-led/my-mvg-departures/blob/main/config.example.toml",
      ),
    ).toBe(
      "https://raw.githubusercontent.com/d-led/my-mvg-departures/main/config.example.toml",
    );

    expect(
      normalizeConfigUrl(
        "https://github.com/d-led/my-mvg-departures/blob/main/spa/configs/berlin-alexanderplatz.toml",
      ),
    ).toBe(
      "https://raw.githubusercontent.com/d-led/my-mvg-departures/main/spa/configs/berlin-alexanderplatz.toml",
    );
  });

  it("leaves raw hosts and other servers alone", () => {
    const raw =
      "https://raw.githubusercontent.com/d-led/my-mvg-departures/main/config.example.toml";
    const gist =
      "https://gist.githubusercontent.com/someone/abc123/raw/config.toml";

    expect(normalizeConfigUrl(raw)).toBe(raw);
    expect(normalizeConfigUrl(gist)).toBe(gist);
    expect(normalizeConfigUrl("https://example.com/config.toml")).toBe(
      "https://example.com/config.toml",
    );
  });

  it("reads a gist page from its raw host", () => {
    expect(normalizeConfigUrl("https://gist.github.com/someone/abc123")).toBe(
      "https://gist.githubusercontent.com/someone/abc123/raw",
    );
  });

  it("does not pretend to know unsupported GitHub pages", () => {
    expect(rawConfigUrl(new URL("https://github.com/d-led"))).toBeNull();
    expect(
      rawConfigUrl(new URL("https://github.com/d-led/repo/tree/main")),
    ).toBeNull();
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
