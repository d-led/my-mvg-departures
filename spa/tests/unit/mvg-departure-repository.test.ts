import { describe, it, expect, vi, beforeEach } from "vitest";
import { MvgDepartureRepository } from "../../src/adapters/mvg/mvg-departure-repository.js";

describe("MvgDepartureRepository", () => {
  let repository: MvgDepartureRepository;

  beforeEach(() => {
    repository = new MvgDepartureRepository();
  });

  it("should fetch departures from MVG API", async () => {
    // Mock fetch
    const mockResponse = [
      {
        realtimeDepartureTime: Date.now() + 300000,
        plannedDepartureTime: Date.now() + 300000,
        delayInMinutes: 0,
        platform: "1",
        realtime: true,
        label: "U6",
        destination: "Garching-Forschungszentrum",
        transportType: "UBAHN",
        cancelled: false,
        messages: [],
        stopPointGlobalId: "de:09162:1110:1:1",
      },
    ];

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    });

    const departures = await repository.getDepartures("de:09162:1110");

    expect(departures).toHaveLength(1);
    expect(departures[0].line).toBe("U6");
    expect(departures[0].destination).toBe("Garching-Forschungszentrum");
    expect(departures[0].transportType).toBe("U-Bahn");
  });

  it("reports API errors so callers can retry and surface them", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
    });

    await expect(repository.getDepartures("de:09162:1110")).rejects.toThrow(
      "MVG API error: 500 Internal Server Error",
    );
  });

  it("reports departures it cannot parse instead of silently dropping the stop", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [{ label: "U6", destination: "Garching" }],
    });

    await expect(repository.getDepartures("de:09162:1110")).rejects.toThrow(
      "realtimeDepartureTime is required but was undefined",
    );
  });

  it("should parse delay correctly", async () => {
    const mockResponse = [
      {
        realtimeDepartureTime: Date.now() + 600000,
        plannedDepartureTime: Date.now() + 300000,
        delayInMinutes: 5,
        platform: "2",
        realtime: true,
        label: "S1",
        destination: "Freising",
        transportType: "SBAHN",
        cancelled: false,
        messages: [],
      },
    ];

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    });

    const departures = await repository.getDepartures("de:09162:1110");

    expect(departures[0].delaySeconds).toBe(300); // 5 minutes * 60
  });

  it("keeps the stand number of a bus departure that has no platform", async () => {
    const time = Date.now() + 300000;
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [
        {
          realtimeDepartureTime: time,
          plannedDepartureTime: time,
          stopPositionNumber: 10,
          realtime: true,
          label: "220",
          destination: "Winning, Riegerweg/Altersheim",
          transportType: "REGIONAL_BUS",
          cancelled: false,
          messages: [],
        },
      ],
    });

    const [departure] = await repository.getDepartures("de:09162:1110");

    expect(departure.platform).toBeNull();
    expect(departure.stopPosition).toBe("10");
  });

  it("keeps the platform of a rail departure, which has no stand number", async () => {
    const time = Date.now() + 300000;
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [
        {
          realtimeDepartureTime: time,
          plannedDepartureTime: time,
          platform: 2,
          realtime: true,
          label: "U2",
          destination: "Messestadt Ost",
          transportType: "UBAHN",
          cancelled: false,
          messages: [],
        },
      ],
    });

    const [departure] = await repository.getDepartures("de:09162:1110");

    expect(departure.platform).toBe("2");
    expect(departure.stopPosition).toBeNull();
  });
});
