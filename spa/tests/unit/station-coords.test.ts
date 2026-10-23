import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

const STATION_ID = "de:09162:1108";
const station = {
  globalId: STATION_ID,
  name: "Chiemgaustraße",
  place: "München",
  latitude: 48.106_716,
  longitude: 11.596_325,
};

function stubStationApi() {
  const fetchMock = vi.fn(async () => ({
    ok: true,
    json: async () => station,
  }));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

async function loadStationCoords() {
  return import("../../src/utils/station-coords.js");
}

describe("station coordinates", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("answers several groups of one station with a single lookup", async () => {
    const fetchMock = stubStationApi();
    const { getStationCoords } = await loadStationCoords();

    const results = await Promise.all([
      getStationCoords(STATION_ID, "Chiemgaustr."),
      getStationCoords(STATION_ID, "Chiemgaustr."),
      getStationCoords(STATION_ID, "Chiemgaustr."),
    ]);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(results).toEqual([
      { lat: station.latitude, lng: station.longitude },
      { lat: station.latitude, lng: station.longitude },
      { lat: station.latitude, lng: station.longitude },
    ]);
  });

  it("serves later calls from the cache", async () => {
    const fetchMock = stubStationApi();
    const { getStationCoords } = await loadStationCoords();

    await getStationCoords(STATION_ID, "Chiemgaustr.");
    await getStationCoords(STATION_ID, "Chiemgaustr.");

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("treats the stop points of one station as one place", async () => {
    const fetchMock = stubStationApi();
    const { getStationCoords, getCachedCoords } = await loadStationCoords();

    await getStationCoords(`${STATION_ID}:4:4`, "Chiemgaustr.");
    await getStationCoords(`${STATION_ID}:5:5`, "Chiemgaustr.");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(getCachedCoords(`${STATION_ID}:5:5`)).toEqual({
      lat: station.latitude,
      lng: station.longitude,
    });
  });
});
