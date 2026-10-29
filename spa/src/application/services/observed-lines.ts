import type { Departure } from "../../domain/models/departure.js";

/** A line a stop serves, and the destinations it has been seen going to. */
export interface ObservedLine {
  line: string;
  transportType: string;
  destinations: string[];
}

/**
 * The lines behind a stop's departures, each with its destinations.
 *
 * This is what the configurator offers instead of a blank text field: the
 * departures the API just showed say which lines a heading can be built from,
 * and one pattern is enough for a line whose destinations do not matter ("18"
 * covers "18 Gondrellplatz" and "18 Stachus" alike).
 */
export function observedLines(departures: Departure[]): ObservedLine[] {
  const byLine = new Map<
    string,
    { transportType: string; destinations: Set<string> }
  >();

  for (const departure of departures) {
    const line = departure.line.trim();
    if (line === "") {
      continue;
    }

    const seen = byLine.get(line) ?? {
      transportType: departure.transportType,
      destinations: new Set<string>(),
    };
    const destination = departure.destination.trim();
    if (destination !== "") {
      seen.destinations.add(destination);
    }
    byLine.set(line, seen);
  }

  return [...byLine.entries()]
    .map(([line, seen]) => ({
      line,
      transportType: seen.transportType,
      destinations: [...seen.destinations].sort((a, b) =>
        a.localeCompare(b, "de"),
      ),
    }))
    .sort((a, b) => compareLines(a.line, b.line));
}

/**
 * Line numbers read as numbers, so "9" comes before "18" and "139", and a line
 * that starts with a letter ("N44", "X30") comes last - it is the exception a
 * reader looks for after the regular ones.
 */
function compareLines(a: string, b: string): number {
  const numberA = leadingNumber(a);
  const numberB = leadingNumber(b);

  if (numberA !== null && numberB !== null && numberA !== numberB) {
    return numberA - numberB;
  }
  if (numberA !== null && numberB === null) {
    return -1;
  }
  if (numberA === null && numberB !== null) {
    return 1;
  }
  return a.localeCompare(b, "de");
}

function leadingNumber(line: string): number | null {
  const digits = /^\d+/.exec(line)?.[0];

  return digits === undefined ? null : Number(digits);
}

/** The pattern that puts every departure of a line under one heading. */
export function linePattern(line: string): string {
  return line.trim();
}

/** The pattern that picks one destination of a line. */
export function destinationPattern(line: string, destination: string): string {
  return `${line.trim()} ${destination.trim()}`;
}
