import { describe, it, expect, beforeEach, vi } from "vitest";
import { LocalStorageCache } from "../../src/adapters/storage/local-storage-cache.js";
import { createDeparture } from "../../src/domain/models/departure.js";

describe("LocalStorageCache", () => {
  let cache: LocalStorageCache;
  let storage: Record<string, string>;

  beforeEach(() => {
    storage = {};
    cache = new LocalStorageCache();

    // Mock localStorage
    global.localStorage = {
      getItem: vi.fn((key: string) => storage[key] ?? null),
      setItem: vi.fn((key: string, value: string) => {
        storage[key] = value;
      }),
      removeItem: vi.fn((key: string) => {
        delete storage[key];
      }),
      clear: vi.fn(() => {
        storage = {};
      }),
      get length() {
        return Object.keys(storage).length;
      },
      key: vi.fn((index: number) => Object.keys(storage)[index] ?? null),
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any;
  });

  it("should store and retrieve departures", async () => {
    const now = new Date();
    const departures = [
      createDeparture({
        time: new Date(now.getTime() + 300000),
        plannedTime: new Date(now.getTime() + 300000),
        line: "U6",
        destination: "Garching",
        transportType: "U-Bahn",
      }),
    ];

    await cache.set("de:09162:1110", departures);

    const cached = await cache.get("de:09162:1110");

    expect(cached).not.toBeNull();
    expect(cached!.length).toBe(1);
    expect(cached![0].line).toBe("U6");
  });

  it("should return null for expired cache", async () => {
    const now = new Date();
    const departures = [
      createDeparture({
        time: new Date(now.getTime() + 300000),
        plannedTime: new Date(now.getTime() + 300000),
        line: "U6",
        destination: "Garching",
        transportType: "U-Bahn",
      }),
    ];

    // Set with very short TTL
    await cache.set("de:09162:1110", departures, 0);

    // Wait a bit and check
    await new Promise((resolve) => setTimeout(resolve, 10));

    const cached = await cache.get("de:09162:1110");

    expect(cached).toBeNull();
  });

  it("should clear all cache entries", async () => {
    await cache.set("de:09162:1110", []);
    await cache.set("de:09162:1056", []);

    await cache.clear();

    const cached1 = await cache.get("de:09162:1110");
    const cached2 = await cache.get("de:09162:1056");

    expect(cached1).toBeNull();
    expect(cached2).toBeNull();
  });
});
