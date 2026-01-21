import type { DepartureCache } from "../../domain/ports/departure-cache.js";
import type { Departure } from "../../domain/models/departure.js";

const CACHE_PREFIX = "mvg_departures_cache_";
const CACHE_TTL_PREFIX = "mvg_departures_cache_ttl_";
const DEFAULT_TTL_SECONDS = 60;

export class LocalStorageCache implements DepartureCache {
  async get(stationId: string): Promise<Departure[] | null> {
    try {
      const cacheKey = `${CACHE_PREFIX}${stationId}`;
      const ttlKey = `${CACHE_TTL_PREFIX}${stationId}`;

      const cached = localStorage.getItem(cacheKey);
      const ttlStr = localStorage.getItem(ttlKey);

      if (!cached || !ttlStr) {
        return null;
      }

      const ttl = parseInt(ttlStr, 10);
      if (Date.now() > ttl) {
        // Expired
        localStorage.removeItem(cacheKey);
        localStorage.removeItem(ttlKey);
        return null;
      }

      const departures = JSON.parse(cached) as Array<{
        time: string | number;
        plannedTime: string | number;
        [key: string]: unknown;
      }>;
      // Convert date strings back to Date objects
      return departures.map((d) => ({
        ...d,
        time: new Date(d.time),
        plannedTime: new Date(d.plannedTime),
      })) as Departure[];
    } catch (error) {
      console.error(`Failed to get cache for ${stationId}:`, error);
      return null;
    }
  }

  async set(
    stationId: string,
    departures: Departure[],
    ttlSeconds: number = DEFAULT_TTL_SECONDS,
  ): Promise<void> {
    try {
      const cacheKey = `${CACHE_PREFIX}${stationId}`;
      const ttlKey = `${CACHE_TTL_PREFIX}${stationId}`;

      const ttl = Date.now() + ttlSeconds * 1000;
      localStorage.setItem(cacheKey, JSON.stringify(departures));
      localStorage.setItem(ttlKey, ttl.toString());
    } catch (error) {
      console.error(`Failed to set cache for ${stationId}:`, error);
      // If storage is full, try to clear old entries
      if (
        error instanceof DOMException &&
        error.name === "QuotaExceededError"
      ) {
        await this.clear();
        // Retry once
        try {
          const cacheKey = `${CACHE_PREFIX}${stationId}`;
          const ttlKey = `${CACHE_TTL_PREFIX}${stationId}`;
          const ttl = Date.now() + ttlSeconds * 1000;
          localStorage.setItem(cacheKey, JSON.stringify(departures));
          localStorage.setItem(ttlKey, ttl.toString());
        } catch (retryError) {
          console.error(`Failed to set cache after clearing:`, retryError);
        }
      }
    }
  }

  async clear(): Promise<void> {
    try {
      const keys: string[] = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (
          key &&
          (key.startsWith(CACHE_PREFIX) || key.startsWith(CACHE_TTL_PREFIX))
        ) {
          keys.push(key);
        }
      }
      keys.forEach((key) => localStorage.removeItem(key));
    } catch (error) {
      console.error("Failed to clear cache:", error);
    }
  }
}
