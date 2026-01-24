import type { RouteConfiguration } from "./route-configuration.js";
import type { OnTheRunConfiguration } from "./on-the-run-configuration.js";

export interface AppConfig {
  routes: RouteConfiguration[];
  onTheRun?: OnTheRunConfiguration;
  defaultDisplay?: {
    title?: string;
    theme?: "light" | "dark" | "auto";
    refreshIntervalSeconds?: number;
    bannerColor?: string;
  };
  api?: {
    sleepMsBetweenCalls?: number;
    apiProvider?: string;
  };
}
