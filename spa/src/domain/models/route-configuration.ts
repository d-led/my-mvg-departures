import type { StopConfiguration } from "./stop-configuration.js";

export interface DisplayConfiguration {
  title?: string;
  theme?: "light" | "dark" | "auto";
  departuresPerPage?: number;
  pageRotationSeconds?: number;
  timeFormatToggleSeconds?: number;
  paginationEnabled?: boolean;
  fillVerticalSpace?: boolean;
  fontScalingFactorWhenFilling?: number;
  randomHeaderColors?: boolean;
  headerBackgroundBrightness?: number;
  refreshIntervalSeconds?: number;
  bannerColor?: string;
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
