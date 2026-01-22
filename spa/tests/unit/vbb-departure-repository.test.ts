import { describe, it, expect, vi, beforeEach } from "vitest";
import { VbbDepartureRepository } from "../../src/adapters/vbb/vbb-departure-repository.js";

describe("VbbDepartureRepository", () => {
  let repository: VbbDepartureRepository;

  beforeEach(() => {
    repository = new VbbDepartureRepository();
    vi.clearAllMocks();
  });

  it("should fetch departures from VBB API", async () => {
    const now = new Date();
    const departureTime = new Date(now.getTime() + 5 * 60 * 1000); // 5 minutes from now

    const mockResponse = {
      departures: [
        {
          when: departureTime.toISOString(),
          plannedWhen: departureTime.toISOString(),
          line: {
            name: "U5",
            product: "subway",
          },
          direction: "Hauptbahnhof",
          platform: "1",
          cancelled: false,
          realtime: true,
          remarks: [],
        },
      ],
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    });

    const departures = await repository.getDepartures("900000009102");

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining(
        "v6.bvg.transport.rest/stops/900000009102/departures",
      ),
      expect.any(Object),
    );
    expect(departures).toHaveLength(1);
    expect(departures[0].line).toBe("U5");
    expect(departures[0].transportType).toBe("U-Bahn");
    expect(departures[0].destination).toBe("Hauptbahnhof");
    expect(departures[0].platform).toBe("1");
  });

  it("should handle API errors gracefully", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
    });

    const departures = await repository.getDepartures("900000009102");

    expect(departures).toEqual([]);
  });

  it("should parse delay correctly", async () => {
    const now = new Date();
    const plannedTime = new Date(now.getTime() + 5 * 60 * 1000); // 5 minutes from now
    const actualTime = new Date(now.getTime() + 10 * 60 * 1000); // 10 minutes from now (5 min delay)

    const mockResponse = {
      departures: [
        {
          when: actualTime.toISOString(),
          plannedWhen: plannedTime.toISOString(),
          line: {
            name: "S1",
            product: "suburban",
          },
          direction: "Potsdam",
          platform: "2",
          cancelled: false,
          realtime: true,
          remarks: [],
        },
      ],
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    });

    const departures = await repository.getDepartures("900000009102");

    expect(departures[0].delaySeconds).toBe(300); // 5 minutes = 300 seconds
    expect(departures[0].transportType).toBe("S-Bahn");
  });
});
