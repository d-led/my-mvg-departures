import { describe, it, expect, afterEach, vi } from "vitest";
import { fetchVbbStationPosition } from "../../src/adapters/vbb/vbb-station-coordinates.js";

const STATION_URL = "https://v6.bvg.transport.rest/stops/900100003";

function jsonResponse(body: unknown, ok = true): Response {
  return { ok, status: ok ? 200 : 404, json: async () => body } as Response;
}

describe("VBB stop positions", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("reads a stop's position from the single-stop endpoint", async () => {
    const fetchMock = vi.fn<(url: string) => Promise<Response>>(async () =>
      jsonResponse({
        name: "S+U Alexanderplatz Bhf (Berlin)",
        location: { latitude: 52.521508, longitude: 13.411267 },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const position = await fetchVbbStationPosition("900100003");

    expect(fetchMock.mock.calls[0][0]).toBe(STATION_URL);
    expect(position).toEqual({ latitude: 52.521508, longitude: 13.411267 });
  });

  it("reports nothing for a stop the API does not know", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ message: "not found" }, false)),
    );

    expect(await fetchVbbStationPosition("000000000")).toBeNull();
  });

  it("reports nothing when the answer carries no position", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ name: "Somewhere" })),
    );

    expect(await fetchVbbStationPosition("900100003")).toBeNull();
  });
});
