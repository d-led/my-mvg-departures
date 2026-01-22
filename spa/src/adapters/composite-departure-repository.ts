import type { DepartureRepository } from "../domain/ports/departure-repository.js";
import type { StopConfiguration } from "../domain/models/stop-configuration.js";
import { MvgDepartureRepository } from "./mvg/mvg-departure-repository.js";
import { VbbDepartureRepository } from "./vbb/vbb-departure-repository.js";
import { UnsupportedDepartureRepository } from "./unsupported-departure-repository.js";
// TODO: Add DB repository when implemented
// import { DbDepartureRepository } from "./db/db-departure-repository.js";

/**
 * Composite repository that routes to the correct API based on stop configuration.
 * Matches the Python version's CompositeDepartureRepository behavior.
 */
export class CompositeDepartureRepository implements DepartureRepository {
  private readonly repositories: Map<string, DepartureRepository> = new Map();
  private readonly stopConfigs: Map<string, StopConfiguration>;
  private readonly unsupportedProviders: Set<string> = new Set();

  constructor(stopConfigs: StopConfiguration[]) {
    // Build station_id to config mapping
    this.stopConfigs = new Map();
    for (const config of stopConfigs) {
      this.stopConfigs.set(config.stationId, config);
      // Also map by base station ID if this is a stop_point_global_id
      const baseId = this.extractBaseStationId(config.stationId);
      if (baseId !== config.stationId && !this.stopConfigs.has(baseId)) {
        this.stopConfigs.set(baseId, config);
      }
    }

    // Initialize repositories for each unique API provider
    this.initializeRepositories();
  }

  private extractBaseStationId(stationId: string): string {
    // Extract base station ID from a potential stop_point_global_id
    // Format: de:09162:1108:3:3 -> de:09162:1108
    const parts = stationId.split(":");
    if (
      parts.length >= 5 &&
      parts[parts.length - 1] === parts[parts.length - 2]
    ) {
      return parts.slice(0, 3).join(":");
    }
    return stationId;
  }

  private createRepositoryForProvider(
    apiProvider: string,
  ): DepartureRepository {
    // Normalize to lowercase
    const provider = apiProvider.toLowerCase();

    if (provider === "db") {
      // TODO: Implement DbDepartureRepository
      this.unsupportedProviders.add("DB");
      return new UnsupportedDepartureRepository("DB");
    }

    if (provider === "vbb") {
      return new VbbDepartureRepository();
    }

    // Default to MVG (also handles "mvg" explicitly)
    return new MvgDepartureRepository();
  }

  getUnsupportedProviders(): string[] {
    return Array.from(this.unsupportedProviders);
  }

  private initializeRepositories(): void {
    // Create repositories for each unique API provider
    const repoCache = new Map<string, DepartureRepository>();

    for (const [stationId, stopConfig] of this.stopConfigs) {
      const apiProvider = (stopConfig.apiProvider ?? "mvg").toLowerCase();

      // Create repository if we haven't seen this API provider
      if (!repoCache.has(apiProvider)) {
        repoCache.set(
          apiProvider,
          this.createRepositoryForProvider(apiProvider),
        );
      }

      // Map this station_id (including base IDs) to the appropriate repository
      this.repositories.set(stationId, repoCache.get(apiProvider)!);
    }
  }

  private getRepository(stationId: string): DepartureRepository {
    // Get the appropriate repository for a station
    const stopConfig = this.stopConfigs.get(stationId);
    if (!stopConfig) {
      // Fallback to MVG if station not found in config
      console.warn(
        `Station ${stationId} not found in config, using MVG as fallback`,
      );
      return new MvgDepartureRepository();
    }

    const repo = this.repositories.get(stationId);
    if (repo) {
      return repo;
    }

    // Fallback to MVG if repository not found
    return new MvgDepartureRepository();
  }

  async getDepartures(
    stationId: string,
    options?: {
      limit?: number;
      offsetMinutes?: number;
      transportTypes?: string[];
      durationMinutes?: number;
    },
  ) {
    const repository = this.getRepository(stationId);
    return repository.getDepartures(stationId, options);
  }
}
