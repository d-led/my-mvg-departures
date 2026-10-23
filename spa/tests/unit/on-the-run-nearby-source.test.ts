import { describe, it, expect } from "vitest";
import { nearbySourceFor } from "../../src/adapters/on-the-run-nearby-source.js";
import { MvgStationRepository } from "../../src/adapters/mvg/mvg-station-repository.js";
import { VbbStationRepository } from "../../src/adapters/vbb/vbb-station-repository.js";

describe("nearbySourceFor", () => {
  it("stays in Munich when the config names no adapter", () => {
    const source = nearbySourceFor(undefined);

    expect(source.adapter).toBe("mvg");
    expect(source.repository).toBeInstanceOf(MvgStationRepository);
  });

  it("looks stops up in Berlin when the config asks for VBB", () => {
    const source = nearbySourceFor(["vbb"]);

    expect(source.adapter).toBe("vbb");
    expect(source.repository).toBeInstanceOf(VbbStationRepository);
  });

  it("takes the first configured adapter that can find stops", () => {
    expect(nearbySourceFor(["vbb", "mvg"]).adapter).toBe("vbb");
    expect(nearbySourceFor(["mvg", "vbb"]).adapter).toBe("mvg");
  });

  it("says which adapters could have answered when none can", async () => {
    const source = nearbySourceFor(["db"]);

    await expect(
      source.repository.getNearbyStations(52.5, 13.4),
    ).rejects.toThrow(
      "on_the_run cannot find nearby stops with db; use one of mvg, vbb",
    );
  });
});
