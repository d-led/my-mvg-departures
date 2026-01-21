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

  it("should handle API errors gracefully", async () => {
    // Suppress console.error for this test since we're testing error handling
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
    });

    const departures = await repository.getDepartures("de:09162:1110");

    expect(departures).toHaveLength(0);
    expect(consoleSpy).toHaveBeenCalled();

    consoleSpy.mockRestore();
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
});
