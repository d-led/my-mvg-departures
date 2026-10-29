import { describe, expect, it } from "vitest";
import { createDeparture } from "../../src/domain/models/departure.js";
import {
  destinationPattern,
  linePattern,
  observedLines,
} from "../../src/application/services/observed-lines.js";

function departure(line: string, destination: string, transportType = "TRAM") {
  const time = new Date("2026-10-28T20:00:00Z");

  return createDeparture({
    time,
    plannedTime: time,
    line,
    destination,
    transportType,
  });
}

describe("observedLines", () => {
  it("names every line once, with the destinations it was seen going to", () => {
    const lines = observedLines([
      departure("18", "Gondrellplatz"),
      departure("18", "Stachus"),
      departure("18", "Gondrellplatz"),
      departure("54", "Münchner Freiheit"),
    ]);

    expect(lines).toEqual([
      {
        line: "18",
        transportType: "TRAM",
        destinations: ["Gondrellplatz", "Stachus"],
      },
      {
        line: "54",
        transportType: "TRAM",
        destinations: ["Münchner Freiheit"],
      },
    ]);
  });

  it("reads line numbers as numbers, and letters after them", () => {
    const lines = observedLines([
      departure("139", "Messestadt West"),
      departure("N44", "Ostbahnhof"),
      departure("9", "Sendlinger Tor"),
      departure("18", "Stachus"),
    ]);

    expect(lines.map((line) => line.line)).toEqual(["9", "18", "139", "N44"]);
  });

  it("leaves out a departure that names no line", () => {
    expect(observedLines([departure("  ", "Stachus")])).toEqual([]);
  });
});

describe("heading patterns", () => {
  it("aggregates a whole line by its number", () => {
    expect(linePattern("18")).toBe("18");
  });

  it("picks one destination of a line", () => {
    expect(destinationPattern("18", "Stachus")).toBe("18 Stachus");
  });
});
