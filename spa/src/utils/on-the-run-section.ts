/**
 * The "Next to me" page lives in one optional `[[on_the_run]]` table. Deleting
 * it (by hand, or by an editor that rewrote the file) used to mean losing the
 * page for good; these helpers bring it back, or take it away on purpose.
 */

import {
  belongsTo,
  leadInStart,
  readTomlTables,
  renderToml,
  tableLinesEnd,
} from "./toml-sections.js";

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

/** Removes the page and the comment block that documents it. */
export function removeOnTheRunSection(toml: string): string {
  const lines = toml.split("\n");
  const removed = new Set<number>();

  for (const table of readTomlTables(lines)) {
    if (!belongsTo(table.name, ON_THE_RUN_TABLE)) {
      continue;
    }
    const start = leadInStart(lines, table.headerLine);
    const end = tableLinesEnd(lines, table);
    for (let line = start; line < end; line += 1) {
      removed.add(line);
    }
  }

  if (removed.size === 0) {
    return toml;
  }

  return renderToml(lines, removed, new Map());
}
