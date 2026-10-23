import { describe, it, expect, vi, afterEach } from "vitest";
import { VbbStationRepository } from "../../src/adapters/vbb/vbb-station-repository.js";

const ALEXANDERPLATZ = { latitude: 52.521_918_4, longitude: 13.413_214_7 };

const ALEXANDERPLATZ_STOPS = [
  {
    type: "stop",
    id: "900100005",
    name: "U Alexanderplatz (Berlin) [Tram]",
    location: { latitude: 52.522_083, longitude: 13.414_593 },
    distance: 94,
  },
  {
    type: "stop",
    id: "900100003",
    name: "S+U Alexanderplatz Bhf (Berlin)",
    location: { latitude: 52.521_9, longitude: 13.413_5 },
    distance: 139,
  },
];

function jsonResponse(body: unknown, ok = true, status = 200): Response {
  return {
    ok,
    status,
    statusText: ok ? "OK" : "Service Unavailable",
    json: async () => body,
  } as unknown as Response;
}

function stubFetch(body: unknown, ok = true, status = 200) {
  const fetchMock = vi.fn<(url: string) => Promise<Response>>(async () =>
    jsonResponse(body, ok, status),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("VbbStationRepository nearby stops", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the stop ids, positions and distances the API ranks", async () => {
    stubFetch(ALEXANDERPLATZ_STOPS);

    const stations = await new VbbStationRepository().getNearbyStations(
      ALEXANDERPLATZ.latitude,
      ALEXANDERPLATZ.longitude,
    );

    expect(stations).toEqual([
      {
        id: "900100005",
        name: "U Alexanderplatz (Berlin) [Tram]",
        latitude: 52.522_083,
        longitude: 13.414_593,
        distanceMeters: 94,
      },
      {
        id: "900100003",
        name: "S+U Alexanderplatz Bhf (Berlin)",
        latitude: 52.521_9,
        longitude: 13.413_5,
        distanceMeters: 139,
      },
    ]);
  });

  it("asks BVG for the stops within a kilometre of the position", async () => {
    const fetchMock = stubFetch(ALEXANDERPLATZ_STOPS);

    await new VbbStationRepository().getNearbyStations(
      ALEXANDERPLATZ.latitude,
      ALEXANDERPLATZ.longitude,
    );

    const requested = new URL(fetchMock.mock.calls[0]![0]);
    expect(`${requested.origin}${requested.pathname}`).toBe(
      "https://v6.bvg.transport.rest/locations/nearby",
    );
    expect(Object.fromEntries(requested.searchParams)).toEqual({
      latitude: "52.5219184",
      longitude: "13.4132147",
      distance: "1000",
      results: "20",
      stops: "true",
      addresses: "false",
      poi: "false",
    });
  });

  it("leaves out whatever is not a stop", async () => {
    stubFetch([
      {
        type: "location",
        id: "980083872",
        name: "Märkisches Museum, Am Köllnischen Park 5, 10179 Berlin",
        location: { latitude: 52.512, longitude: 13.408 },
        distance: 20,
      },
      { type: "stop", id: "900100014", name: "U Märkisches Museum (Berlin)" },
      ...ALEXANDERPLATZ_STOPS,
    ]);

    const stations = await new VbbStationRepository().getNearbyStations(
      ALEXANDERPLATZ.latitude,
      ALEXANDERPLATZ.longitude,
    );

    expect(stations.map((station) => station.id)).toEqual([
      "900100005",
      "900100003",
    ]);
  });

  it("reports a failing API instead of pretending no stop is nearby", async () => {
    stubFetch({}, false, 503);

    await expect(
      new VbbStationRepository().getNearbyStations(
        ALEXANDERPLATZ.latitude,
        ALEXANDERPLATZ.longitude,
      ),
    ).rejects.toThrow("VBB API error: 503 Service Unavailable");
  });
});
