/**
 * The "Next to me" page lives in one optional `[[on_the_run]]` table. Deleting
 * it (by hand, or by an editor that rewrote the file) used to mean losing the
 * page for good; this brings it back.
 */

import { belongsTo, readTomlTables } from "./toml-sections.js";

const ON_THE_RUN_TABLE = "on_the_run";

/** The block written when the page is added back. */
const ON_THE_RUN_SECTION = [
  "# Nearby departures, using the browser's location",
  "[[on_the_run]]",
  "radius_meters = 50",
  "max_departures_per_stop = 8",
  "max_departures_per_route = 2",
  "refresh_interval_seconds = 20",
];

export function hasOnTheRun(toml: string): boolean {
  return readTomlTables(toml.split("\n")).some((table) =>
    belongsTo(table.name, ON_THE_RUN_TABLE),
  );
}

/** Adds the page when it is missing; an existing one is kept as it is. */
export function addOnTheRunSection(toml: string): string {
  if (hasOnTheRun(toml)) {
    return toml;
  }

  if (!toml.trim()) {
    return [...ON_THE_RUN_SECTION, ""].join("\n");
  }

  return `${toml.trimEnd()}\n\n${ON_THE_RUN_SECTION.join("\n")}\n`;
}
