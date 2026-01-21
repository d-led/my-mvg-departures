import type { DepartureRepository } from "../domain/ports/departure-repository.js";
import type { Departure } from "../domain/models/departure.js";

/**
 * Repository for unsupported API providers.
 * Returns empty arrays instead of throwing errors, allowing the UI to display a message.
 */
export class UnsupportedDepartureRepository implements DepartureRepository {
  constructor(private readonly provider: string) {}

  async getDepartures(
    stationId: string,
    options?: {
      limit?: number;
      offsetMinutes?: number;
      transportTypes?: string[];
      durationMinutes?: number;
    },
  ): Promise<Departure[]> {
    // Mark parameters as intentionally unused (required by interface but not used)
    void stationId;
    void options;
    // Return empty array instead of throwing - UI will handle displaying the message
    return [];
  }

  getUnsupportedProvider(): string {
    return this.provider;
  }
}
