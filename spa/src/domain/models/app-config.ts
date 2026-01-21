import type { RouteConfiguration } from "./route-configuration.js";

export interface AppConfig {
  routes: RouteConfiguration[];
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
