import type { DepartureRepository } from "../../domain/ports/departure-repository.js";
import type { Departure } from "../../domain/models/departure.js";
import { createDeparture } from "../../domain/models/departure.js";
import type { VbbApiDeparture, VbbApiResponse } from "./vbb-api-types.js";

export class VbbDepartureRepository implements DepartureRepository {
  private readonly baseUrl = "https://v6.bvg.transport.rest";

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
    const durationMinutes = options?.durationMinutes ?? 60;
    const offsetMinutes = options?.offsetMinutes ?? 0;

    // Build request parameters (matches Python version)
    const params = this.buildRequestParams(offsetMinutes, durationMinutes);
    const url = new URL(
      `${this.baseUrl}/stops/${encodeURIComponent(stationId)}/departures`,
    );
    // Add query parameters
    Object.entries(params).forEach(([key, value]) => {
      url.searchParams.append(key, String(value));
    });

    console.log(`[VBB API] Fetching: ${url.toString()}`);
    try {
      const response = await fetch(url.toString(), {
        headers: {
          accept: "application/json",
          "user-agent": "Mozilla/5.0",
        },
      });

      if (!response.ok) {
        throw new Error(
          `VBB API error: ${response.status} ${response.statusText}`,
        );
      }

      const data: VbbApiResponse = await response.json();
      const departuresData = data.departures ?? [];

      console.log(
        `[VBB API] Received ${departuresData.length} departures for ${stationId}`,
      );

      return this.convertDeparturesList(departuresData, limit);
    } catch (error) {
      console.error(`Failed to fetch departures for ${stationId}:`, error);
      return [];
    }
  }

  private buildRequestParams(
    offsetMinutes: number,
    durationMinutes: number,
  ): Record<string, string | number> {
    // Match Python version: _build_request_params
    const params: Record<string, string | number> = {
      duration: durationMinutes,
      results: 500, // Get up to 500 departures to have enough for all routes
    };

    const now = new Date();
    if (offsetMinutes > 0) {
      const futureTime = new Date(now.getTime() + offsetMinutes * 60 * 1000);
      params.when = futureTime.toISOString();
    } else {
      params.when = now.toISOString();
    }

    return params;
  }

  private parseDepartureTime(
    depData: VbbApiDeparture,
  ): { when: Date; plannedWhen: Date } | null {
    // Match Python version: _parse_departure_time
    const whenStr = depData.when || depData.plannedWhen;
    const plannedWhenStr = depData.plannedWhen || depData.when;

    if (!whenStr || !plannedWhenStr) {
      return null;
    }

    // Parse ISO 8601 strings, handling Z suffix (matches Python: replace("Z", "+00:00"))
    const when = new Date(whenStr.replace("Z", "+00:00"));
    const plannedWhen = new Date(plannedWhenStr.replace("Z", "+00:00"));

    if (isNaN(when.getTime()) || isNaN(plannedWhen.getTime())) {
      return null;
    }

    return { when, plannedWhen };
  }

  private calculateDelay(when: Date, plannedWhen: Date): number | null {
    // Match Python version: _calculate_delay
    const delaySeconds = Math.floor(
      (when.getTime() - plannedWhen.getTime()) / 1000,
    );
    return delaySeconds > 0 ? delaySeconds : null;
  }

  private extractLineInfo(depData: VbbApiDeparture): {
    lineName: string;
    transportType: string;
  } {
    // Match Python version: _extract_line_info
    const lineObj = depData.line ?? {};
    const lineName = lineObj.name || lineObj.id || "";
    const product = (lineObj.product || "").toLowerCase();

    const transportTypeMap: Record<string, string> = {
      subway: "U-Bahn",
      suburban: "S-Bahn",
      bus: "Bus",
      tram: "Tram",
      ferry: "Ferry",
      regional: "Regional",
      express: "Express",
    };
    const transportType =
      transportTypeMap[product] ??
      (product ? product.charAt(0).toUpperCase() + product.slice(1) : "");

    return { lineName, transportType };
  }

  private extractDestination(depData: VbbApiDeparture): string {
    // Match Python version: _extract_destination
    const direction = depData.direction || "";
    const destObj = depData.destination;

    let destName = "";
    if (destObj && typeof destObj === "object") {
      destName = destObj.name || "";
    }

    if (direction) {
      return direction;
    }
    if (destName) {
      return destName;
    }
    return "";
  }

  private extractMessages(depData: VbbApiDeparture): string[] {
    // Match Python version: _extract_messages
    const remarks = depData.remarks ?? [];
    const messages: string[] = [];

    for (const remark of remarks) {
      if (typeof remark === "string") {
        messages.push(remark);
      } else if (remark && typeof remark === "object" && remark.text) {
        messages.push(remark.text);
      }
    }

    return messages;
  }

  private parseDeparture(depData: VbbApiDeparture): Departure | null {
    // Match Python version: _convert_departure
    const timeData = this.parseDepartureTime(depData);
    if (!timeData) {
      return null;
    }

    const { when, plannedWhen } = timeData;
    const delaySeconds = this.calculateDelay(when, plannedWhen);
    const { lineName, transportType } = this.extractLineInfo(depData);
    const destination = this.extractDestination(depData);
    const messages = this.extractMessages(depData);

    const platform = depData.platform != null ? String(depData.platform) : null;
    const isCancelled = depData.cancelled ?? false;
    // Match Python: is_realtime = delay_seconds is not None or dep_data.get("realtime", False)
    const isRealtime = delaySeconds !== null || (depData.realtime ?? false);

    return createDeparture({
      time: when,
      plannedTime: plannedWhen,
      delaySeconds,
      platform,
      isRealtime,
      line: lineName,
      destination,
      transportType,
      icon: "", // VBB API doesn't provide icons (matches Python)
      isCancelled,
      messages,
      stopPointGlobalId: null, // VBB API doesn't provide this
    });
  }

  private convertDeparturesList(
    departuresData: VbbApiDeparture[],
    limit: number,
  ): Departure[] {
    // Match Python version: _convert_departures_list
    const departures: Departure[] = [];
    for (const depData of departuresData.slice(0, limit)) {
      try {
        const departure = this.parseDeparture(depData);
        if (departure) {
          departures.push(departure);
        }
      } catch (error) {
        console.warn("Error processing VBB departure:", error);
      }
    }
    return departures;
  }
}
