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
        return [];
      }

      return results.map((result) => this.parseDeparture(result));
    } catch (error) {
      console.error(`Failed to fetch departures for ${stationId}:`, error);
      return [];
    }
  }

  private parseDeparture(result: MvgApiDeparture): Departure {
    const time = new Date(
      result.realtimeDepartureTime ?? result.plannedDepartureTime,
    );
    const plannedTime = new Date(result.plannedDepartureTime);
    const delayMinutes = result.delayInMinutes ?? 0;
    const delaySeconds = delayMinutes * 60;

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

    return createDeparture({
      time,
      plannedTime,
      delaySeconds,
      platform: result.platform ?? null,
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
