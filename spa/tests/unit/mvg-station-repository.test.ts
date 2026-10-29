import { describe, it, expect, vi, afterEach } from "vitest";
import { MvgStationRepository } from "../../src/adapters/mvg/mvg-station-repository.js";

const STATION_URL =
  "https://www.mvg.de/api/bgw-pt/v3/stations/de%3A09162%3A1108";
const LOCATIONS_URL =
  "https://www.mvg.de/api/bgw-pt/v3/locations?query=Chiemgaustr.";

function jsonResponse(body: unknown, ok = true): Response {
  return {
    ok,
    status: ok ? 200 : 404,
    json: async () => body,
  } as unknown as Response;
}

const station = {
  globalId: "de:09162:1108",
  name: "Chiemgaustraße",
  place: "München",
  latitude: 48.106_716,
  longitude: 11.596_325,
};

describe("MvgStationRepository coordinates", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("reads a station's coordinates from the single-station endpoint", async () => {
    const fetchMock = vi.fn<(url: string) => Promise<Response>>(async () =>
      jsonResponse(station),
    );
    vi.stubGlobal("fetch", fetchMock);

    const location = await new MvgStationRepository().getStationByQuery(
      "Chiemgaustr.",
      "de:09162:1108:3:3",
    );

    expect(location).toEqual({
      id: "de:09162:1108",
      name: "Chiemgaustraße",
      place: "München",
      latitude: 48.106_716,
      longitude: 11.596_325,
    });
    // A stop point resolves through its station, not through the catalogue.
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0]?.[0]).toBe(STATION_URL);
  });

  it("falls back to the location search when the station lookup has nothing", async () => {
    const fetchMock = vi.fn(async (url: string) =>
      url === STATION_URL
        ? jsonResponse({ status: 404 }, false)
        : jsonResponse([
            {
              name: "Chiemgaustraße 135",
              type: "ADDRESS",
              latitude: 48.1,
              longitude: 11.6,
            },
            { ...station, type: "STATION" },
          ]),
    );
    vi.stubGlobal("fetch", fetchMock);

    const location = await new MvgStationRepository().getStationByQuery(
      "Chiemgaustr.",
      "de:09162:1108:3:3",
    );

    expect(location?.id).toBe("de:09162:1108");
    expect(fetchMock.mock.calls[1]?.[0]).toBe(LOCATIONS_URL);
  });

  it("ignores matches without coordinates", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse([
          { name: "Chiemgau Apotheke", type: "POI" },
          { ...station, type: "STATION" },
        ]),
      ),
    );

    const location = await new MvgStationRepository().getStationByQuery(
      "Chiemgaustr.",
    );

    expect(location?.latitude).toBe(48.106_716);
  });

  it("returns nothing instead of throwing when the API fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      }),
    );

    await expect(
      new MvgStationRepository().getStationByQuery("Chiemgaustr."),
    ).resolves.toBeNull();
  });
});

describe("MvgStationRepository search", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("offers every station a name matches, with its place", async () => {
    const fetchMock = vi.fn<(url: string) => Promise<Response>>(async () =>
      jsonResponse([
        { ...station, type: "STATION" },
        {
          globalId: "de:09162:1110",
          name: "Giesing",
          place: "München",
          latitude: 48.110_861,
          longitude: 11.595_247,
        },
        { name: "Chiemgau Apotheke", type: "POI" },
      ]),
    );
    vi.stubGlobal("fetch", fetchMock);

    const stations = await new MvgStationRepository().searchStations(
      "Chiemgau",
    );

    expect(stations).toEqual([
      {
        id: "de:09162:1108",
        name: "Chiemgaustraße",
        place: "München",
        latitude: 48.106_716,
        longitude: 11.596_325,
      },
      {
        id: "de:09162:1110",
        name: "Giesing",
        place: "München",
        latitude: 48.110_861,
        longitude: 11.595_247,
      },
    ]);
    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "https://www.mvg.de/api/bgw-pt/v3/locations?query=Chiemgau&locationTypes=STATION",
    );
  });

  it("asks the API nothing for an empty name", async () => {
    const fetchMock = vi.fn(async () => jsonResponse([]));
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      new MvgStationRepository().searchStations("   "),
    ).resolves.toEqual([]);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
