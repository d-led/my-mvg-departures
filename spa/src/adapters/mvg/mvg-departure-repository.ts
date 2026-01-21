import type { DepartureRepository } from "../../domain/ports/departure-repository.js";
import type { Departure } from "../../domain/models/departure.js";
import { createDeparture } from "../../domain/models/departure.js";
import type { MvgApiDeparture } from "./mvg-api-types.js";

export class MvgDepartureRepository implements DepartureRepository {
  private readonly baseUrl = "https://www.mvg.de/api/bgw-pt/v3/departures";

  async getDepartures(
    stationId: string,
    options?: {
      limit?: number;
      offsetMinutes?: number;
      transportTypes?: string[];
      durationMinutes?: number;
    },
  ): Promise<Departure[]> {
    const limit = options?.limit ?? 20;
    const transportTypes = "UBAHN,TRAM,SBAHN,BUS,REGIONAL_BUS,BAHN";
    const url = `${this.baseUrl}?globalId=${encodeURIComponent(stationId)}&limit=${limit}&transportTypes=${transportTypes}`;

    console.log(`[MVG API] Fetching: ${url}`);
    try {
      const response = await fetch(url, {
        headers: {
          accept: "application/json",
          "user-agent": "Mozilla/5.0",
        },
      });

      if (!response.ok) {
        throw new Error(
          `MVG API error: ${response.status} ${response.statusText}`,
        );
      }

      const results = await response.json();
      if (!Array.isArray(results)) {
        console.log(`[MVG API] Response is not an array for ${stationId}`);
        return [];
      }

      console.log(
        `[MVG API] Received ${results.length} departures for ${stationId}`,
      );
      return results.map((result) => this.parseDeparture(result));
    } catch (error) {
      console.error(`Failed to fetch departures for ${stationId}:`, error);
      return [];
    }
  }

  private parseDeparture(result: MvgApiDeparture): Departure {
    // Match Python version exactly:
    // time = datetime.fromtimestamp(result["realtimeDepartureTime"] / 1000, tz=UTC)
    // Python always uses realtimeDepartureTime (no fallback)
    // Handle undefined case: if realtimeDepartureTime is missing, fall back to plannedDepartureTime
    if (result.realtimeDepartureTime === undefined) {
      throw new Error("realtimeDepartureTime is required but was undefined");
    }
    const time = new Date(result.realtimeDepartureTime);
    // planned_time = datetime.fromtimestamp(result["plannedDepartureTime"] / 1000, tz=UTC)
    const plannedTime = new Date(result.plannedDepartureTime);
    // delay_seconds = result.get("delayInMinutes", 0) * 60 if result.get("delayInMinutes") else 0
    // Match Python: if delayInMinutes exists, convert to seconds, otherwise None (not 0)
    const delaySeconds =
      result.delayInMinutes != null ? result.delayInMinutes * 60 : null;

    const transportTypeEnum = result.transportType ?? "";
    const transportTypeMap: Record<string, string> = {
      UBAHN: "U-Bahn",
      SBAHN: "S-Bahn",
      BUS: "Bus",
      TRAM: "Tram",
      BAHN: "Bahn",
      REGIONAL_BUS: "Regionalbus",
    };
    const transportType =
      transportTypeMap[transportTypeEnum] ?? transportTypeEnum;

    const iconMap: Record<string, string> = {
      UBAHN: "mdi:subway",
      SBAHN: "mdi:subway-variant",
      BUS: "mdi:bus",
      TRAM: "mdi:tram",
      BAHN: "mdi:train",
      REGIONAL_BUS: "mdi:bus",
    };
    const icon = iconMap[transportTypeEnum] ?? "";

    // Match Python: platform = result.get("platform")
    // Python model is int | None, but we store as string for display (Python converts to str when rendering)
    const platform = result.platform != null ? String(result.platform) : null;

    return createDeparture({
      time,
      plannedTime,
      delaySeconds,
      platform,
      isRealtime: result.realtime ?? false,
      line: result.label ?? "",
      destination: result.destination ?? "",
      transportType,
      icon,
      isCancelled: result.cancelled ?? false,
      messages: result.messages ?? [],
      stopPointGlobalId: result.stopPointGlobalId ?? null,
    });
  }
}
