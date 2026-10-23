import type {
  DisplayConfiguration,
  RouteConfiguration,
} from "./route-configuration.js";
import type { OnTheRunConfiguration } from "./on-the-run-configuration.js";

/**
 * The SPA's configuration: every route carries its own stops, and one optional
 * `[display]` table holds the settings all routes inherit.
 *
 * Server-only tables (`[api]`, `[inky]`, `[server]`, ...) have no meaning here and
 * are not part of this model.
 */
export interface AppConfig {
  /** Defaults for all routes; a route's own display settings win. */
  display?: DisplayConfiguration;
  routes: RouteConfiguration[];
  onTheRun?: OnTheRunConfiguration;
}
