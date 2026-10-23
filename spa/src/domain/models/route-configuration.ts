import type { StopConfiguration } from "./stop-configuration.js";

export interface DisplayConfiguration {
  title?: string;
  theme?: "light" | "dark" | "auto";
  /** Seconds the relative time stays on screen before switching to absolute and back. */
  timeFormatToggleSeconds?: number;
  fillVerticalSpace?: boolean;
  fontScalingFactorWhenFilling?: number;
  randomHeaderColors?: boolean;
  headerBackgroundBrightness?: number;
  refreshIntervalSeconds?: number;
  /** Tries per stop and refresh cycle before the stop counts as failed (default 3). */
  fetchRetryAttempts?: number;
  /** Pause between those tries in milliseconds (default 500). */
  fetchRetryDelayMs?: number;
  splitShowDelay?: boolean;
  fontSizeRouteNumber?: string;
  fontSizeDestination?: string;
  fontSizePlatform?: string;
  fontSizeTime?: string;
  fontSizeStopHeader?: string;
  fontSizeDirectionHeader?: string;
  fontSizePaginationIndicator?: string;
  fontSizeCountdownText?: string;
  fontSizeDelayAmount?: string;
  fontSizeNoDepartures?: string;
  fontSizeStatusHeader?: string;
  routeIconDisplay?: "icon_with_text" | "badge" | "none";
}

export interface RouteConfiguration {
  path: string;
  display?: DisplayConfiguration;
  stops: StopConfiguration[];
  refreshIntervalSeconds?: number;
  isOnTheRun?: boolean;
}
