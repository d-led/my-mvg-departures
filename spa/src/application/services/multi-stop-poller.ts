import type { DepartureRepository } from "../../domain/ports/departure-repository.js";
import type { DepartureCache } from "../../domain/ports/departure-cache.js";
import type { StopConfiguration } from "../../domain/models/stop-configuration.js";
import type { GroupedDepartures } from "../../domain/models/grouped-departures.js";
import { DepartureGroupingService } from "./departure-grouping-service.js";

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
  ) {}

  async start(): Promise<void> {
    if (this.isRunning) {
      console.warn("Poller already running, ignoring start() call");
      return;
    }

    console.log("MultiStopPoller.start() called - setting isInitialPoll = true");
    this.isRunning = true;
    this.isInitialPoll = true;

    // Do initial poll immediately (always fetch fresh, don't use cache)
    console.log("Starting initial poll (isInitialPoll =", this.isInitialPoll, ")");
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

  private async poll(): Promise<void> {
    const allGroups: GroupedDepartures[] = [];
    let successCount = 0;
    let errorCount = 0;

    // Process stops SEQUENTIALLY to preserve TOML order (matches Python: for stop_config in self.stop_configs)
    // This ensures stops appear in the same order as defined in the TOML configuration
    console.log(`Polling ${this.stopConfigs.length} stop(s)${this.isInitialPoll ? " (initial poll - fetching fresh)" : ""}`);
    
    for (const stopConfig of this.stopConfigs) {
      console.log(`Polling stop: ${stopConfig.stationName} (${stopConfig.stationId})`);
      try {
        // On initial poll, always fetch fresh data (don't use cache)
        // On subsequent polls, check cache first
        if (!this.isInitialPoll) {
          const cached = await this.cache.get(stopConfig.stationId);
          if (cached && cached.length > 0) {
            console.log(`Using cached data for ${stopConfig.stationName} (${cached.length} departures)`);
            const groups = this.groupingService.groupDepartures(cached, stopConfig);
            // Add groups from this stop in order (preserves direction order from TOML)
            groups.forEach((group) => {
              allGroups.push({ ...group });
            });
            successCount++;
            continue;
          }
        } else {
          console.log(`Initial poll: fetching fresh data for ${stopConfig.stationName} (skipping cache)`);
        }

        // Fetch fresh data
        console.log(`Fetching fresh data from API for ${stopConfig.stationName}...`);
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
          const groups = this.groupingService.groupDepartures(departures, stopConfig);
          // Add groups from this stop in order
          groups.forEach((group) => {
            allGroups.push({ ...group });
          });
          successCount++;
        }
      } catch (error) {
        errorCount++;
        const err = error instanceof Error ? error : new Error(String(error));
        console.error(`API poll error for ${stopConfig.stationName}:`, err);
      }
    }

    // Generate header colors for non-first headers (matches Python's _generate_header_colors)
    this.generateHeaderColors(allGroups);

    // Update state with combined groups
    this.allGroups = allGroups;
    console.log(`Combined ${allGroups.length} direction groups from ${successCount} successful stop(s), ${errorCount} error(s)`);
    this.callbacks.onUpdate([...allGroups]);
  }

  private generateHeaderColors(groups: GroupedDepartures[]): void {
    // Generate header colors for non-first headers (matches Python: _generate_header_colors)
    // Only generate colors if random_header_colors is enabled for the stop
    for (let i = 1; i < groups.length; i++) {
      const group = groups[i];
      // Check if any stop config has random_header_colors enabled
      // For now, we'll generate colors for all non-first headers if any stop has it enabled
      // This is a simplification - in Python, each stop can have its own setting
      const stopConfig = this.stopConfigs.find(s => s.stationName === group.stopName);
      if (stopConfig?.randomHeaderColors) {
        const headerText = `${group.stopName} → ${group.directionName}`;
        group.headerColor = this.generatePastelColor(
          headerText,
          stopConfig.headerBackgroundBrightness ?? 0.7,
          stopConfig.randomColorSalt ?? 0
        );
      }
    }
  }

  private generatePastelColor(text: string, brightness: number = 0.7, salt: number = 0): string {
    // Generate a stable pastel color from text using hash-based mapping (matches Python's generate_pastel_color_from_text)
    // Use a simple hash function (MD5 would be ideal but requires a library)
    // This implementation uses a djb2-like hash for consistency
    let hash = 5381;
    const str = `${text}:${salt}`;
    for (let i = 0; i < str.length; i++) {
      hash = ((hash << 5) + hash) + str.charCodeAt(i);
    }
    
    // Use hash as a 32-bit unsigned integer
    const hashInt = Math.abs(hash >>> 0);
    
    // Extract parts for HSL calculation (matches Python's _calculate_hsl_from_hash)
    const hashPart1 = (hashInt >> 16) & 0xFFFF; // Upper 16 bits
    const hashPart2 = hashInt & 0xFFFF; // Lower 16 bits
    
    const hueBase = hashPart1 % 360;
    const hueVariation = (hashPart2 % 60) - 30; // -30 to +30 degrees
    const hue = (hueBase + hueVariation) % 360;
    
    const saturation = 55 + (hashInt % 26); // 55-80%
    
    const brightnessAdjusted = Math.pow(brightness, 1.5);
    const baseLightnessMin = 30 + (brightnessAdjusted * 45); // 30-75
    const baseLightnessMax = 40 + (brightnessAdjusted * 45); // 40-85
    const lightnessRange = Math.max(1, baseLightnessMax - baseLightnessMin);
    const lightness = baseLightnessMin + (hashInt % lightnessRange);
    
    // Convert HSL to RGB (matches Python's _hsl_to_rgb)
    const h = hue / 360;
    const s = saturation / 100;
    const l = lightness / 100;
    
    const c = (1 - Math.abs(2 * l - 1)) * s;
    const x = c * (1 - Math.abs((h * 6) % 2 - 1));
    const m = l - c / 2;
    
    let r = 0, g = 0, b = 0;
    if (h < 1/6) { r = c; g = x; b = 0; }
    else if (h < 2/6) { r = x; g = c; b = 0; }
    else if (h < 3/6) { r = 0; g = c; b = x; }
    else if (h < 4/6) { r = 0; g = x; b = c; }
    else if (h < 5/6) { r = x; g = 0; b = c; }
    else { r = c; g = 0; b = x; }
    
    r = Math.round((r + m) * 255);
    g = Math.round((g + m) * 255);
    b = Math.round((b + m) * 255);
    
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
  }
}
