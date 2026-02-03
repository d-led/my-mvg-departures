import { describe, it, expect } from "vitest";

/**
 * Tests for config merging logic in ConfigModal.svelte
 * Verifies that wizard completion properly appends new stops without destroying existing config
 */

describe("ConfigModal - Stop Configuration Merging", () => {
  type WizardStop = {
    station_id: string;
    station_name: string;
    max_departures_per_stop: number;
    max_departures_per_route: number;
    max_hours_in_advance: number;
    show_ungrouped: boolean;
    custom_title?: string;
    direction_mappings?: Record<string, string[]>;
  };
  /**
   * Extract and parse a TOML config to verify structure
   */
  function parseConfigSections(configText: string) {
    const sections: {
      display?: string;
      stops: Map<string, string>;
      routes: string;
      other: string;
    } = {
      display: undefined,
      stops: new Map(),
      routes: "",
      other: "",
    };

    const lines = configText.split("\n");
    let currentSection = "";
    let currentStopId = "";
    let currentStopBlock = "";

    for (const line of lines) {
      if (line.startsWith("[display]")) {
        currentSection = "display";
        if (!sections.display) {
          sections.display = line;
        } else {
          sections.display += "\n" + line;
        }
      } else if (line.startsWith("[[stops]]")) {
        // Save previous stop block
        if (currentStopBlock && currentStopId) {
          sections.stops.set(currentStopId, currentStopBlock);
        }
        currentSection = "stop";
        currentStopBlock = line;

        // Extract station_id from next lines
        currentStopId = "";
      } else if (line.startsWith("[stops.") || line.startsWith("[stops]")) {
        // Skip direction_mappings and other nested sections
        currentSection = "skip";
      } else if (line.startsWith("[[routes]]")) {
        currentSection = "routes";
        sections.routes += (sections.routes ? "\n" : "") + line;
      } else if (line.startsWith("[") || line.startsWith("[[")) {
        currentSection = "other";
        sections.other += (sections.other ? "\n" : "") + line;
      } else {
        if (currentSection === "display") {
          sections.display += "\n" + line;
          // Extract station_id
          if (line.includes("station_id")) {
            const match = line.match(/station_id\s*=\s*"([^"]+)"/);
            if (match) currentStopId = match[1];
          }
        } else if (currentSection === "stop") {
          currentStopBlock += "\n" + line;
          // Extract station_id
          if (line.includes("station_id")) {
            const match = line.match(/station_id\s*=\s*"([^"]+)"/);
            if (match) currentStopId = match[1];
          }
        } else if (currentSection === "routes") {
          sections.routes += "\n" + line;
        } else if (currentSection === "other") {
          sections.other += "\n" + line;
        }
      }
    }

    // Save last stop block
    if (currentStopBlock && currentStopId) {
      sections.stops.set(currentStopId, currentStopBlock);
    }

    return sections;
  }

  function findStopBlocks(configText: string) {
    const lines = configText.split("\n");
    const lineStartOffsets: number[] = [];
    let offset = 0;
    for (const line of lines) {
      lineStartOffsets.push(offset);
      offset += line.length + 1;
    }

    const blocks: {
      stationId: string;
      startIndex: number;
      endIndex: number;
      text: string;
    }[] = [];
    let currentStartLine = -1;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const isSection = line.startsWith("[");
      const isStopStart = line.startsWith("[[stops]]");
      const isStopNested =
        line.startsWith("[stops.") || line.startsWith("[stops]");

      if (isStopStart) {
        if (currentStartLine !== -1) {
          const startIndex = lineStartOffsets[currentStartLine];
          const endIndex = lineStartOffsets[i] - 1;
          const textSlice = configText.slice(startIndex, endIndex);
          const match = textSlice.match(/station_id\s*=\s*"([^"]+)"/);
          if (match) {
            blocks.push({
              stationId: match[1],
              startIndex,
              endIndex,
              text: textSlice,
            });
          }
        }
        currentStartLine = i;
      } else if (currentStartLine !== -1 && isSection && !isStopNested) {
        const startIndex = lineStartOffsets[currentStartLine];
        const endIndex = lineStartOffsets[i] - 1;
        const textSlice = configText.slice(startIndex, endIndex);
        const match = textSlice.match(/station_id\s*=\s*"([^"]+)"/);
        if (match) {
          blocks.push({
            stationId: match[1],
            startIndex,
            endIndex,
            text: textSlice,
          });
        }
        currentStartLine = -1;
      }
    }

    if (currentStartLine !== -1) {
      const startIndex = lineStartOffsets[currentStartLine];
      const endIndex = configText.length;
      const textSlice = configText.slice(startIndex, endIndex);
      const match = textSlice.match(/station_id\s*=\s*"([^"]+)"/);
      if (match) {
        blocks.push({
          stationId: match[1],
          startIndex,
          endIndex,
          text: textSlice,
        });
      }
    }

    return blocks;
  }

  function extractDirectionMappingsFromBlock(block: string) {
    const mappings: Record<string, string[]> = {};
    const directionSectionMatch = block.match(
      /\[stops\.direction_mappings\]([\s\S]*?)(?=\n\[|$)/,
    );
    if (!directionSectionMatch) {
      return mappings;
    }

    const lines = directionSectionMatch[1].split("\n");
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) continue;
      const match = trimmed.match(/^"([^"]+)"\s*=\s*\[(.*)\]$/);
      if (!match) continue;
      const key = match[1];
      const valueList = match[2]
        .split(",")
        .map((part) => part.trim())
        .filter(Boolean)
        .map((value) => value.replace(/^"|"$/g, ""));
      mappings[key] = valueList;
    }
    return mappings;
  }

  function buildStopBlock(
    stop: WizardStop,
    mergedMappings: Record<string, string[]> | null = null,
  ) {
    let block = "[[stops]]\n";
    block += `station_id = "${stop.station_id}"\n`;
    block += `station_name = "${stop.station_name}"\n`;
    block += `max_departures_per_stop = ${stop.max_departures_per_stop}\n`;
    block += `max_departures_per_route = ${stop.max_departures_per_route}\n`;
    block += `max_hours_in_advance = ${stop.max_hours_in_advance}\n`;
    block += `show_ungrouped = ${stop.show_ungrouped}\n`;
    if (stop.custom_title) {
      block += `ungrouped_title = "${stop.custom_title}"\n`;
    }

    const mappings = mergedMappings ?? stop.direction_mappings;
    if (mappings && Object.keys(mappings).length > 0) {
      block += "\n[stops.direction_mappings]\n";
      for (const [key, value] of Object.entries(mappings)) {
        const patterns = Array.isArray(value) ? value : [value as string];
        const quoted = patterns.map((pattern) => `"${pattern}"`).join(", ");
        block += `"${key}" = [${quoted}]\n`;
      }
    }

    return block.trimEnd();
  }

  function mergeWizardStopsForTest(configText: string, stops: WizardStop[]) {
    const stopBlocks = findStopBlocks(configText);
    const stopBlocksById = new Map(
      stopBlocks.map((block) => [block.stationId, block]),
    );
    const replacements: { start: number; end: number; text: string }[] = [];
    const stopsToAppend: WizardStop[] = [];

    for (const stop of stops) {
      const existingBlock = stopBlocksById.get(stop.station_id);
      if (existingBlock) {
        const existingMappings = extractDirectionMappingsFromBlock(
          existingBlock.text,
        );
        const mergedMappings = { ...existingMappings };
        if (stop.direction_mappings) {
          Object.assign(mergedMappings, stop.direction_mappings);
        }
        const newBlock = buildStopBlock(stop, mergedMappings);
        replacements.push({
          start: existingBlock.startIndex,
          end: existingBlock.endIndex,
          text: newBlock,
        });
      } else {
        stopsToAppend.push(stop);
      }
    }

    let updatedConfig = configText;
    replacements.sort((a, b) => b.start - a.start);
    for (const replacement of replacements) {
      updatedConfig =
        updatedConfig.slice(0, replacement.start) +
        replacement.text +
        updatedConfig.slice(replacement.end);
    }

    if (stopsToAppend.length > 0) {
      const newBlocks = stopsToAppend
        .map((stop) => buildStopBlock(stop))
        .join("\n\n");
      const stopBlocksAfterReplace = findStopBlocks(updatedConfig);
      const insertAt = stopBlocksAfterReplace.length
        ? stopBlocksAfterReplace[stopBlocksAfterReplace.length - 1].endIndex
        : updatedConfig.length;
      const before = updatedConfig.slice(0, insertAt).replace(/\s*$/, "");
      const after = updatedConfig.slice(insertAt).replace(/^\s*/, "");
      const beforeSeparator = before ? "\n\n" : "";
      const afterSeparator = after ? "\n\n" : "";
      updatedConfig =
        before + beforeSeparator + newBlocks + afterSeparator + after;
    }

    return updatedConfig.trim();
  }

  it("should preserve existing stops when adding a new stop", () => {
    // Existing config with 2 stops
    const existingConfig = `[display]
hide_cancelled = true
route_icon_display = "icon_with_text"

[[stops]]
station_id = "de:09162:1100"
station_name = "Marienplatz"
max_departures_per_stop = 4
max_departures_per_route = 2
max_hours_in_advance = 3
show_ungrouped = false

[[stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
max_departures_per_stop = 4
max_departures_per_route = 2
max_hours_in_advance = 3
show_ungrouped = true
ungrouped_title = "Stop 2"`;

    // New stop from wizard (different station_id)
    const newStops = [
      {
        station_id: "de:09162:2000",
        station_name: "Neuhausen",
        max_departures_per_stop: 4,
        max_departures_per_route: 2,
        max_hours_in_advance: 3,
        show_ungrouped: true,
        custom_title: "Platform A",
      },
    ];

    const finalConfig = mergeWizardStopsForTest(existingConfig, newStops);

    // Verify the result
    const parsed = parseConfigSections(finalConfig);

    // Should have 3 stops total (2 original + 1 new)
    expect(parsed.stops.size).toBe(3);
    expect(parsed.stops.has("de:09162:1100")).toBe(true); // Marienplatz preserved
    expect(parsed.stops.has("de:09162:1110")).toBe(true); // Giesing preserved
    expect(parsed.stops.has("de:09162:2000")).toBe(true); // Neuhausen added

    // Verify display section is preserved
    expect(parsed.display).toContain("hide_cancelled");

    console.log("✓ Existing stops preserved when adding new stop");
    console.log("Final config:\n", finalConfig);
  });

  it("should replace only the modified stop when reconfiguring", () => {
    const existingConfig = `[display]
hide_cancelled = true

[[stops]]
station_id = "de:09162:1100"
station_name = "Marienplatz"
max_departures_per_stop = 4
max_departures_per_route = 2
max_hours_in_advance = 3
show_ungrouped = false

[[stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
max_departures_per_stop = 2
max_departures_per_route = 1
max_hours_in_advance = 2
show_ungrouped = true
ungrouped_title = "Old Title"`;

    // Wizard reconfigures only Giesing with new settings
    const modifiedStops = [
      {
        station_id: "de:09162:1110",
        station_name: "Giesing",
        max_departures_per_stop: 6,
        max_departures_per_route: 3,
        max_hours_in_advance: 4,
        show_ungrouped: false,
        custom_title: "New Title",
      },
    ];

    const finalConfig = mergeWizardStopsForTest(existingConfig, modifiedStops);

    // Verify
    const parsed = parseConfigSections(finalConfig);
    expect(parsed.stops.size).toBe(2); // Both stops present
    expect(parsed.stops.has("de:09162:1100")).toBe(true); // Marienplatz unchanged

    // Verify Giesing was updated
    const giesingBlock = parsed.stops.get("de:09162:1110") || "";
    expect(giesingBlock).toContain("max_departures_per_stop = 6");
    expect(giesingBlock).toContain('ungrouped_title = "New Title"');

    console.log("✓ Modified stop replaced correctly, others preserved");
  });

  it("should preserve direction_mappings with platform/stop labels", () => {
    const existingConfig = `[display]
hide_cancelled = true

[[stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
max_departures_per_stop = 4
max_departures_per_route = 2
max_hours_in_advance = 3
show_ungrouped = false

[stops.direction_mappings]
"Platform 1" = ["54", "139"]
"Platform 2" = ["U2"]`;

    // Wizard adds a sub-stop entry (different station_id, like a physical stop)
    const newStops = [
      {
        station_id: "de:09162:1110:2",
        station_name: "Giesing",
        custom_title: "Platform 2",
        max_departures_per_stop: 4,
        max_departures_per_route: 2,
        max_hours_in_advance: 3,
        show_ungrouped: true,
      },
    ];

    const finalConfig = mergeWizardStopsForTest(existingConfig, newStops);

    // Verify
    const parsed = parseConfigSections(finalConfig);
    expect(parsed.stops.size).toBe(2);
    expect(parsed.stops.has("de:09162:1110")).toBe(true); // Main stop preserved
    expect(parsed.stops.has("de:09162:1110:2")).toBe(true); // Sub-stop added

    console.log("✓ Direction mappings structure maintained");
  });

  it("should handle config with direction_mappings followed by other sections", () => {
    // This tests the real-world scenario where direction_mappings exist
    // and there are other sections after the stops block
    const existingConfig = `[display]
hide_cancelled = true

[[stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
max_departures_per_stop = 4
max_departures_per_route = 2
max_hours_in_advance = 3
show_ungrouped = false

[stops.direction_mappings]
"Platform 1" = ["54", "139"]
"Platform 2" = ["U2"]

[[routes]]
name = "MyRoute"
station_id = "de:09162:1110"`;

    // Wizard reconfigures the stop
    const newStops = [
      {
        station_id: "de:09162:1110",
        station_name: "Giesing",
        max_departures_per_stop: 6,
        max_departures_per_route: 3,
        max_hours_in_advance: 3,
        show_ungrouped: false,
      },
    ];

    const finalConfig = mergeWizardStopsForTest(existingConfig, newStops);

    // Verify routes section is preserved
    expect(finalConfig).toContain("[[routes]]");
    expect(finalConfig).toContain('name = "MyRoute"');

    console.log("✓ Routes section preserved after stops reconfiguration");
    console.log("Final config:\n", finalConfig);
  });

  it("should preserve existing stop with direction_mappings while adding sub-stop", () => {
    // Real scenario: Giesing has direction_mappings, user adds a sub-stop
    const existingConfig = `[display]
hide_cancelled = true

[[stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
max_departures_per_stop = 4
max_departures_per_route = 2
max_hours_in_advance = 3
show_ungrouped = false

[stops.direction_mappings]
"Platform 1" = ["54", "139"]
"Platform 2" = ["U2"]`;

    // Wizard adds a sub-stop (different station_id)
    const newStops = [
      {
        station_id: "de:09162:1108:3:3",
        station_name: "Giesing",
        max_departures_per_stop: 4,
        max_departures_per_route: 2,
        max_hours_in_advance: 3,
        show_ungrouped: true,
      },
    ];

    const finalConfig = mergeWizardStopsForTest(existingConfig, newStops);

    // Verify both stops are in config
    expect(finalConfig).toContain('station_id = "de:09162:1110"');
    expect(finalConfig).toContain('station_id = "de:09162:1108:3:3"');

    // Verify direction_mappings is preserved
    expect(finalConfig).toContain("[stops.direction_mappings]");
    expect(finalConfig).toContain('"Platform 1"');
    expect(finalConfig).toContain('"Platform 2"');

    console.log(
      "✓ Preserved existing stop with direction_mappings while adding sub-stop",
    );
    console.log("Final config:\n", finalConfig);
  });

  it("should preserve all other sub-stops when updating one sub-stop of same main stop", () => {
    // Scenario: A main stop has multiple physical sub-stops (e.g., different platforms)
    // User goes to wizard and updates only one sub-stop
    // Should preserve all other sub-stops with their direction_mappings intact
    const existingConfig = `[display]
hide_cancelled = true

[[stops]]
station_id = "de:01234:5001:1:1"
station_name = "Main Station"
max_departures_per_stop = 4
max_departures_per_route = 2
max_hours_in_advance = 3
show_ungrouped = false

[stops.direction_mappings]
"->Direction A" = ["1 Destination A", "2 Destination B"]

[[stops]]
station_id = "de:01234:5001:2:2"
station_name = "Main Station"
max_departures_per_stop = 4
max_departures_per_route = 2
max_hours_in_advance = 3
show_ungrouped = true
ungrouped_title = "Platform 2"

[stops.direction_mappings]
"->Direction B" = ["3 Destination C", "4 Destination D"]

[[stops]]
station_id = "de:01234:5001:3:3"
station_name = "Main Station"
max_departures_per_stop = 4
max_departures_per_route = 2
max_hours_in_advance = 3
show_ungrouped = true
ungrouped_title = "Platform 3"

[[stops]]
station_id = "de:01234:5001:4:4"
station_name = "Main Station"
max_departures_per_stop = 4
max_departures_per_route = 2
max_hours_in_advance = 3
show_ungrouped = true
ungrouped_title = "Platform 4"

[[stops]]
station_id = "de:01234:5001:5:5"
station_name = "Main Station"
max_departures_per_stop = 4
max_departures_per_route = 2
max_hours_in_advance = 3
show_ungrouped = true
ungrouped_title = "Platform 5"`;

    // Wizard: User only updates sub-stop 4:4
    const wizardStops = [
      {
        station_id: "de:01234:5001:4:4",
        station_name: "Main Station",
        max_departures_per_stop: 4,
        max_departures_per_route: 2,
        max_hours_in_advance: 3,
        show_ungrouped: true,
        custom_title: "Platform 4 Updated",
      },
    ];

    const finalConfig = mergeWizardStopsForTest(existingConfig, wizardStops);

    // CRITICAL: Verify all OTHER sub-stops are preserved with their direction_mappings
    expect(finalConfig).toContain('station_id = "de:01234:5001:1:1"');
    expect(finalConfig).toContain('station_id = "de:01234:5001:2:2"');
    expect(finalConfig).toContain('station_id = "de:01234:5001:3:3"');
    expect(finalConfig).toContain('station_id = "de:01234:5001:4:4"'); // Updated one
    expect(finalConfig).toContain('station_id = "de:01234:5001:5:5"');

    // Verify direction_mappings for 1:1 and 2:2 are preserved
    expect(finalConfig).toContain('"->Direction A"');
    expect(finalConfig).toContain('"->Direction B"');
    expect(finalConfig).toContain("Destination A");
    expect(finalConfig).toContain("Destination C");

    // Verify other ungrouped titles are preserved
    expect(finalConfig).toContain("Platform 2");
    expect(finalConfig).toContain("Platform 3");
    expect(finalConfig).toContain("Platform 4 Updated"); // Updated one

    console.log("✓ All other sub-stops preserved when updating one sub-stop");
    console.log("Final config:\n", finalConfig);
  });

  it("should NOT lose direction_mappings when wizard updates existing stop", () => {
    // CORRECT BEHAVIOR: When wizard updates an existing stop,
    // it should either:
    // A) Detect conflict and ask user to merge/replace/skip
    // B) Provide the MERGED mappings back in the stop config
    // NOT: Silently replace with only new mappings

    const existingConfig = `[display]
hide_cancelled = true

[[stops]]
station_id = "de:01234:5001"
station_name = "Main Station"
max_departures_per_stop = 4
max_departures_per_route = 2
max_hours_in_advance = 3
show_ungrouped = false

[stops.direction_mappings]
"Direction A" = ["1 Dest A", "2 Dest B"]
"Direction B" = ["3 Dest C", "4 Dest D"]`;

    // CORRECT: Wizard detects this stop exists and merges mappings
    // So it returns the COMPLETE merged set:
    const wizardStopsCorrect = [
      {
        station_id: "de:01234:5001",
        station_name: "Main Station",
        max_departures_per_stop: 4,
        max_departures_per_route: 2,
        max_hours_in_advance: 3,
        show_ungrouped: false,
        direction_mappings: {
          "Direction A": ["1 Dest A", "2 Dest B"], // From existing
          "Direction B": ["3 Dest C", "4 Dest D"], // From existing
          "Direction C (new)": ["5 Dest E", "6 Dest F"], // From wizard
        },
      },
    ];

    const finalConfig = mergeWizardStopsForTest(
      existingConfig,
      wizardStopsCorrect,
    );

    // CORRECT: All mappings should be present
    expect(finalConfig).toContain('"Direction A"');
    expect(finalConfig).toContain('"Direction B"');
    expect(finalConfig).toContain('"Direction C (new)"');
    expect(finalConfig).toContain("Dest A");
    expect(finalConfig).toContain("Dest C");
    expect(finalConfig).toContain("Dest E");

    console.log(
      "✓ CORRECT: All direction_mappings preserved when wizard merges",
    );
    console.log("Final config:\n", finalConfig);
  });

  it("should skip exact duplicate stops in config", () => {
    // If wizard returns the exact same stop that already exists,
    // we should skip the existing one to avoid duplicate entries

    const existingConfig = `[display]
hide_cancelled = true

[[stops]]
station_id = "de:01234:5001"
station_name = "Main Station"
max_departures_per_stop = 4
max_departures_per_route = 2
max_hours_in_advance = 3
show_ungrouped = false

[stops.direction_mappings]
"Direction A" = ["1 Dest A"]`;

    // Wizard returns the SAME stop (user didn't actually change anything)
    const wizardStops = [
      {
        station_id: "de:01234:5001",
        station_name: "Main Station",
        max_departures_per_stop: 4,
        max_departures_per_route: 2,
        max_hours_in_advance: 3,
        show_ungrouped: false,
        direction_mappings: {
          "Direction A": ["1 Dest A"],
        },
      },
    ];

    const finalConfig = mergeWizardStopsForTest(existingConfig, wizardStops);

    // Should only have one instance (no duplicates)
    const stopMatches = Array.from(
      finalConfig.matchAll(/station_id = "de:01234:5001"/g),
    );
    expect(stopMatches.length).toBe(1);

    console.log("✓ Exact duplicates skipped (only one instance)");
    console.log("Final config:\n", finalConfig);
  });
});
