import type { DepartureRepository } from "../../domain/ports/departure-repository.js";
import type { DepartureCache } from "../../domain/ports/departure-cache.js";
import type { StopConfiguration } from "../../domain/models/stop-configuration.js";
import type { GroupedDepartures } from "../../domain/models/grouped-departures.js";
import type { DisplayConfiguration } from "../../domain/models/route-configuration.js";
import { DepartureGroupingService } from "./departure-grouping-service.js";
import md5 from "md5";

export interface MultiStopPollerCallbacks {
  onUpdate: (groups: GroupedDepartures[]) => void;
  onError: (error: Error) => void;
}

export class MultiStopPoller {
  private intervalId: number | null = null;
  private isRunning = false;
  private allGroups: GroupedDepartures[] = [];
  private isInitialPoll = true;

  constructor(
    private readonly departureRepository: DepartureRepository,
    private readonly cache: DepartureCache,
    private readonly groupingService: DepartureGroupingService,
    private readonly stopConfigs: StopConfiguration[],
    private readonly refreshIntervalSeconds: number,
    private readonly callbacks: MultiStopPollerCallbacks,
    private readonly routeDisplay?: DisplayConfiguration, // Route display config for header color fallback
  ) {}

  async start(): Promise<void> {
    if (this.isRunning) {
      console.warn("Poller already running, ignoring start() call");
      return;
    }

    console.log(
      "MultiStopPoller.start() called - setting isInitialPoll = true",
    );
    this.isRunning = true;
    this.isInitialPoll = true;

    // Do initial poll immediately (always fetch fresh, don't use cache)
    console.log(
      "Starting initial poll (isInitialPoll =",
      this.isInitialPoll,
      ")",
    );
    await this.poll();

    // Mark that initial poll is done
    this.isInitialPoll = false;

    // Then poll periodically (will use cache if available)
    this.intervalId = window.setInterval(() => {
      this.poll().catch((error) => {
        this.callbacks.onError(error);
      });
    }, this.refreshIntervalSeconds * 1000);
  }

  stop(): void {
    if (this.intervalId !== null) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    this.isRunning = false;
    this.isInitialPoll = true; // Reset for next start
  }

  /**
   * Force an immediate refresh (fetch fresh data now, bypassing cache)
   * Useful when page becomes visible after being hidden
   */
  async refreshNow(): Promise<void> {
    if (!this.isRunning) {
      console.warn("Poller not running, cannot refresh");
      return;
    }
    console.log("Forcing immediate refresh (page became visible)");
    // Temporarily set isInitialPoll to bypass cache
    const wasInitialPoll = this.isInitialPoll;
    this.isInitialPoll = true;
    try {
      await this.poll();
    } finally {
      this.isInitialPoll = wasInitialPoll;
    }
  }

  private async poll(): Promise<void> {
    const allGroups: GroupedDepartures[] = [];
    const stopsWithDepartures = new Set<string>(); // Track which stops have departures
    let successCount = 0;
    let errorCount = 0;

    // Process stops SEQUENTIALLY to preserve TOML order (matches Python: for stop_config in self.stop_configs)
    // This ensures stops appear in the same order as defined in the TOML configuration
    console.log(
      `Polling ${this.stopConfigs.length} stop(s)${this.isInitialPoll ? " (initial poll - fetching fresh)" : ""}`,
    );

    for (const stopConfig of this.stopConfigs) {
      console.log(
        `Polling stop: ${stopConfig.stationName} (${stopConfig.stationId})`,
      );
      try {
        // On initial poll, always fetch fresh data (don't use cache)
        // On subsequent polls, check cache first
        if (!this.isInitialPoll) {
          const cached = await this.cache.get(stopConfig.stationId);
          if (cached && cached.length > 0) {
            console.log(
              `Using cached data for ${stopConfig.stationName} (${cached.length} departures)`,
            );
            const groups = this.groupingService.groupDepartures(
              cached,
              stopConfig,
            );
            // Add groups from this stop in order (preserves direction order from TOML)
            groups.forEach((group) => {
              allGroups.push({ ...group });
            });
            if (groups.length > 0) {
              stopsWithDepartures.add(stopConfig.stationName);
            }
            successCount++;
            continue;
          }
        } else {
          console.log(
            `Initial poll: fetching fresh data for ${stopConfig.stationName} (skipping cache)`,
          );
        }

        // Fetch fresh data
        console.log(
          `Fetching fresh data from API for ${stopConfig.stationName}...`,
        );
        const departures = await this.departureRepository.getDepartures(
          stopConfig.stationId,
          {
            limit: stopConfig.maxDeparturesFetch ?? 50,
            offsetMinutes: stopConfig.departureLeewayMinutes ?? 0,
            durationMinutes: stopConfig.fetchMaxMinutesInAdvance ?? 120,
          },
        );

        if (departures.length > 0) {
          // Update cache
          await this.cache.set(stopConfig.stationId, departures, 60);

          // Group departures (preserves direction order from TOML)
          const groups = this.groupingService.groupDepartures(
            departures,
            stopConfig,
          );
          // Add groups from this stop in order
          groups.forEach((group) => {
            allGroups.push({ ...group });
          });
          if (groups.length > 0) {
            stopsWithDepartures.add(stopConfig.stationName);
          }
          successCount++;
        }
      } catch (error) {
        errorCount++;
        const err = error instanceof Error ? error : new Error(String(error));
        console.error(`API poll error for ${stopConfig.stationName}:`, err);
      }
    }

    // Find stops without departures (matches Python: _find_stops_without_departures)
    const stopsWithoutDepartures = this.stopConfigs
      .filter((stop) => !stopsWithDepartures.has(stop.stationName))
      .map((stop) => stop.stationName)
      .sort(); // Sort alphabetically (matches Python: sorted(configured_stops - stops_with_departures))

    // Create empty groups for stops without departures (matches Python template lines 138-145)
    // Python template: header is just {{ stop_name }}, not "StopName → DirectionName"
    for (const stopName of stopsWithoutDepartures) {
      const stopConfig = this.stopConfigs.find(
        (s) => s.stationName === stopName,
      );
      if (stopConfig) {
        allGroups.push({
          directionName: stopName, // For empty groups, directionName = stopName (header will be just stopName)
          stopName: stopConfig.stationName,
          stationId: stopConfig.stationId,
          departures: [], // Empty departures array (matches Python template line 142)
          // Store color settings from stop config
          randomHeaderColors: stopConfig.randomHeaderColors,
          headerBackgroundBrightness: stopConfig.headerBackgroundBrightness,
          randomColorSalt: stopConfig.randomColorSalt,
        });
      }
    }

    // Generate header colors for non-first headers (matches Python's _generate_header_colors)
    this.generateHeaderColors(allGroups);

    // Update state with combined groups
    this.allGroups = allGroups;
    console.log(
      `Combined ${allGroups.length} direction groups from ${successCount} successful stop(s), ${errorCount} error(s), ${stopsWithoutDepartures.length} stop(s) without departures`,
    );
    this.callbacks.onUpdate([...allGroups]);
  }

  private generateHeaderColors(groups: GroupedDepartures[]): void {
    // Generate header colors for non-first headers (matches Python: _generate_header_colors)
    // Python logic: use group-level config if set, otherwise fall back to route display config
    // First header (index 0) ALWAYS uses default banner_color - never generate a color for it
    console.log(
      `[header-colors] Generating colors for ${groups.length} groups, routeDisplay.randomHeaderColors=${this.routeDisplay?.randomHeaderColors}, routeDisplay.headerBackgroundBrightness=${this.routeDisplay?.headerBackgroundBrightness}`,
    );

    for (let i = 1; i < groups.length; i++) {
      const group = groups[i];

      // Use group-level config if set (stored when group was created), otherwise fall back to route display config
      // This matches Python lines 339-349: group_random_colors if group_random_colors is not None else self.random_header_colors
      const useRandomColors =
        group.randomHeaderColors !== undefined &&
        group.randomHeaderColors !== null
          ? group.randomHeaderColors
          : (this.routeDisplay?.randomHeaderColors ?? false);
      const brightness =
        group.headerBackgroundBrightness !== undefined &&
        group.headerBackgroundBrightness !== null
          ? group.headerBackgroundBrightness
          : (this.routeDisplay?.headerBackgroundBrightness ?? 0.7);
      const salt =
        group.randomColorSalt !== undefined && group.randomColorSalt !== null
          ? group.randomColorSalt
          : 0; // Salt is only per-stop, no route-level fallback

      console.log(
        `[header-colors] Group ${i} (${group.stopName} [${group.stationId}] → ${group.directionName}): group.randomHeaderColors=${group.randomHeaderColors}, useRandomColors=${useRandomColors}, brightness=${brightness}, salt=${salt}`,
      );

      if (useRandomColors) {
        // Strip "->" prefix from direction name (matches Python: direction_clean = group.direction_name.lstrip("->"))
        const directionClean = group.directionName.replace(/^->/, "");
        const headerText = `${group.stopName} → ${directionClean}`;
        group.headerColor = this.generatePastelColor(
          headerText,
          brightness,
          salt,
        );
        console.log(
          `[header-colors] Generated color for group ${i}: ${group.headerColor}`,
        );
      } else {
        // Explicitly don't set headerColor - will use default banner_color from CSS
        group.headerColor = undefined;
        console.log(
          `[header-colors] Not generating color for group ${i} (random_header_colors disabled)`,
        );
      }
    }
  }

  private generatePastelColor(
    text: string,
    brightness: number = 0.7,
    salt: number = 0,
  ): string {
    // Generate a stable pastel color from text using hash-based mapping (matches Python's generate_pastel_color_from_text)
    // Use MD5 hashing to match Python version exactly (Python uses hashlib.md5)
    // Python: hash_int = int(hashlib.md5(f"{text}:{salt}".encode()).hexdigest(), 16)
    const str = `${text}:${salt}`;
    const md5Hex = md5(str); // MD5 produces 32 hex characters (128 bits)
    // Convert hex string to BigInt to match Python's int(hexdigest(), 16)
    const hashBigInt = BigInt("0x" + md5Hex);

    // Extract parts for HSL calculation (matches Python's _calculate_hsl_from_hash)
    // Python: hash_part1 = (hash_int >> 16) & 0xFFFF, hash_part2 = hash_int & 0xFFFF
    // Python uses full 128-bit MD5 hash, extracts 16-bit parts
    const hashPart1 = Number((hashBigInt >> 16n) & 0xffffn); // Upper 16 bits
    const hashPart2 = Number(hashBigInt & 0xffffn); // Lower 16 bits

    const hueBase = hashPart1 % 360;
    const hueVariation = (hashPart2 % 60) - 30; // -30 to +30 degrees
    const hue = (hueBase + hueVariation) % 360;

    // Use full hash for saturation and lightness calculations (matches Python)
    const hashInt = Number(hashBigInt & 0xffffffffffffffffn); // Use lower 64 bits for calculations
    const saturation = 55 + (hashInt % 26); // 55-80%

    const brightnessAdjusted = Math.pow(brightness, 1.5);
    const baseLightnessMin = 30 + brightnessAdjusted * 45; // 30-75
    const baseLightnessMax = 40 + brightnessAdjusted * 45; // 40-85
    const lightnessRange = Math.max(1, baseLightnessMax - baseLightnessMin);
    const lightness = baseLightnessMin + (hashInt % lightnessRange);

    // Convert HSL to RGB (matches Python's _hsl_to_rgb)
    const h = hue / 360;
    const s = saturation / 100;
    const l = lightness / 100;

    const c = (1 - Math.abs(2 * l - 1)) * s;
    const x = c * (1 - Math.abs(((h * 6) % 2) - 1));
    const m = l - c / 2;

    let r = 0,
      g = 0,
      b = 0;
    if (h < 1 / 6) {
      r = c;
      g = x;
      b = 0;
    } else if (h < 2 / 6) {
      r = x;
      g = c;
      b = 0;
    } else if (h < 3 / 6) {
      r = 0;
      g = c;
      b = x;
    } else if (h < 4 / 6) {
      r = 0;
      g = x;
      b = c;
    } else if (h < 5 / 6) {
      r = x;
      g = 0;
      b = c;
    } else {
      r = c;
      g = 0;
      b = x;
    }

    r = Math.round((r + m) * 255);
    g = Math.round((g + m) * 255);
    b = Math.round((b + m) * 255);

    return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
  }
}
