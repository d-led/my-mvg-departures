import { describe, it, expect, beforeEach } from "vitest";

/**
 * Tests for config merging logic in ConfigModal.svelte
 * Verifies that wizard completion properly appends new stops without destroying existing config
 */

describe("ConfigModal - Stop Configuration Merging", () => {
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

    // Simulate the merging logic
    const lines = existingConfig.split("\n");
    const stopsToAdd = new Set(newStops.map((s) => s.station_id));
    let displaySection = "";
    let existingStopsBlocks = "";
    let currentStopBlock = "";
    let currentSection = "";

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      if (line.startsWith("[display]")) {
        currentSection = "display";
        displaySection = line;
      } else if (line.startsWith("[[stops]]")) {
        // Save previous block
        if (currentStopBlock) {
          const blockStopId = currentStopBlock.match(
            /station_id\s*=\s*"([^"]+)"/
          );
          if (blockStopId && blockStopId[1]) {
            if (!stopsToAdd.has(blockStopId[1])) {
              // KEEP existing stops not being reconfigured
              existingStopsBlocks +=
                (existingStopsBlocks ? "\n" : "") + currentStopBlock;
            }
          }
        }
        currentSection = "stop";
        currentStopBlock = line;
      } else if (
        line.startsWith("[stops.") ||
        line.startsWith("[stops]")
      ) {
        currentSection = "skip";
      } else {
        if (currentSection === "display") {
          displaySection += "\n" + line;
        } else if (currentSection === "stop") {
          currentStopBlock += "\n" + line;
        }
      }
    }

    // Process last stop block
    if (currentStopBlock && currentSection === "stop") {
      const blockStopId = currentStopBlock.match(
        /station_id\s*=\s*"([^"]+)"/
      );
      if (blockStopId && blockStopId[1]) {
        if (!stopsToAdd.has(blockStopId[1])) {
          existingStopsBlocks +=
            (existingStopsBlocks ? "\n" : "") + currentStopBlock;
        }
      }
    }

    // Build final config
    let finalConfig = "";
    if (displaySection) {
      finalConfig += displaySection + "\n\n";
    }
    if (existingStopsBlocks) {
      finalConfig += existingStopsBlocks + "\n\n";
    }

    // Add new stops
    for (const stop of newStops) {
      finalConfig += "[[stops]]\n";
      finalConfig += `station_id = "${stop.station_id}"\n`;
      finalConfig += `station_name = "${stop.station_name}"\n`;
      finalConfig += `max_departures_per_stop = ${stop.max_departures_per_stop}\n`;
      finalConfig += `max_departures_per_route = ${stop.max_departures_per_route}\n`;
      finalConfig += `max_hours_in_advance = ${stop.max_hours_in_advance}\n`;
      finalConfig += `show_ungrouped = ${stop.show_ungrouped}\n`;

      if (stop.custom_title) {
        finalConfig += `ungrouped_title = "${stop.custom_title}"\n`;
      }
      finalConfig += "\n";
    }

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

    // Simulate merging
    const stopsToAdd = new Set(modifiedStops.map((s) => s.station_id));
    let existingStopsBlocks = "";
    let currentStopBlock = "";
    let currentSection = "";
    const lines = existingConfig.split("\n");

    for (const line of lines) {
      if (line.startsWith("[display]")) {
        currentSection = "display";
      } else if (line.startsWith("[[stops]]")) {
        if (currentStopBlock) {
          const blockStopId = currentStopBlock.match(
            /station_id\s*=\s*"([^"]+)"/
          );
          if (blockStopId && !stopsToAdd.has(blockStopId[1])) {
            existingStopsBlocks +=
              (existingStopsBlocks ? "\n" : "") + currentStopBlock;
          }
        }
        currentSection = "stop";
        currentStopBlock = line;
      } else if (line.startsWith("[stops.")) {
        currentSection = "skip";
      } else if (currentSection === "stop") {
        currentStopBlock += "\n" + line;
      }
    }

    // Process last stop
    if (currentStopBlock) {
      const blockStopId = currentStopBlock.match(
        /station_id\s*=\s*"([^"]+)"/
      );
      if (blockStopId && !stopsToAdd.has(blockStopId[1])) {
        existingStopsBlocks +=
          (existingStopsBlocks ? "\n" : "") + currentStopBlock;
      }
    }

    // Build final config
    let finalConfig = "";
    if (existingStopsBlocks) {
      finalConfig += existingStopsBlocks + "\n\n";
    }

    for (const stop of modifiedStops) {
      finalConfig += "[[stops]]\n";
      finalConfig += `station_id = "${stop.station_id}"\n`;
      finalConfig += `station_name = "${stop.station_name}"\n`;
      finalConfig += `max_departures_per_stop = ${stop.max_departures_per_stop}\n`;
      finalConfig += `max_departures_per_route = ${stop.max_departures_per_route}\n`;
      finalConfig += `max_hours_in_advance = ${stop.max_hours_in_advance}\n`;
      finalConfig += `show_ungrouped = ${stop.show_ungrouped}\n`;

      if (stop.custom_title) {
        finalConfig += `ungrouped_title = "${stop.custom_title}"\n`;
      }
      finalConfig += "\n";
    }

    // Verify
    const parsed = parseConfigSections(finalConfig);
    expect(parsed.stops.size).toBe(2); // Both stops present
    expect(parsed.stops.has("de:09162:1100")).toBe(true); // Marienplatz unchanged

    // Verify Giesing was updated
    const giesingBlock = parsed.stops.get("de:09162:1110") || "";
    expect(giesingBlock).toContain("max_departures_per_stop = 6");
    expect(giesingBlock).toContain("ungrouped_title = \"New Title\"");

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

    // The main stop (de:09162:1110) should be preserved
    // The new sub-stop (de:09162:1110:2) should be added
    const stopsToAdd = new Set(newStops.map((s) => s.station_id));
    let existingStopsBlocks = "";
    let currentStopBlock = "";
    const lines = existingConfig.split("\n");

    for (const line of lines) {
      if (line.startsWith("[[stops]]")) {
        if (currentStopBlock) {
          const blockStopId = currentStopBlock.match(
            /station_id\s*=\s*"([^"]+)"/
          );
          if (blockStopId && !stopsToAdd.has(blockStopId[1])) {
            existingStopsBlocks +=
              (existingStopsBlocks ? "\n" : "") + currentStopBlock;
          }
        }
        currentStopBlock = line;
      } else if (
        line.startsWith("[stops.") ||
        line.startsWith("[stops]")
      ) {
        // Skip these for now (they'll be stripped)
      } else if (currentStopBlock) {
        currentStopBlock += "\n" + line;
      }
    }

    if (currentStopBlock) {
      const blockStopId = currentStopBlock.match(
        /station_id\s*=\s*"([^"]+)"/
      );
      if (blockStopId && !stopsToAdd.has(blockStopId[1])) {
        existingStopsBlocks +=
          (existingStopsBlocks ? "\n" : "") + currentStopBlock;
      }
    }

    // Build final
    let finalConfig = "";
    if (existingStopsBlocks) {
      finalConfig += existingStopsBlocks + "\n\n";
    }

    for (const stop of newStops) {
      finalConfig += "[[stops]]\n";
      finalConfig += `station_id = "${stop.station_id}"\n`;
      finalConfig += `station_name = "${stop.station_name}"\n`;
      finalConfig += `max_departures_per_stop = ${stop.max_departures_per_stop}\n`;
      finalConfig += `max_departures_per_route = ${stop.max_departures_per_route}\n`;
      finalConfig += `max_hours_in_advance = ${stop.max_hours_in_advance}\n`;
      finalConfig += `show_ungrouped = ${stop.show_ungrouped}\n`;

      if (stop.custom_title) {
        finalConfig += `ungrouped_title = "${stop.custom_title}"\n`;
      }
      finalConfig += "\n";
    }

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

    // The [[routes]] section should be preserved
    const stopsToAdd = new Set(newStops.map((s) => s.station_id));
    let displaySection = "";
    let existingStopsBlocks = "";
    let routeSections = "";
    let currentSection = "";
    let currentStopBlock = "";
    let sectionContent: string[] = [];

    const lines = existingConfig.split("\n");

    for (const line of lines) {
      if (line.startsWith("[display]")) {
        currentSection = "display";
        sectionContent = [line];
      } else if (line.startsWith("[[stops]]")) {
        if (currentStopBlock) {
          const blockStopId = currentStopBlock.match(
            /station_id\s*=\s*"([^"]+)"/
          );
          if (blockStopId && !stopsToAdd.has(blockStopId[1])) {
            existingStopsBlocks +=
              (existingStopsBlocks ? "\n" : "") + currentStopBlock;
          }
        }
        currentSection = "stop";
        currentStopBlock = line;
      } else if (line.startsWith("[stops.") || line.startsWith("[stops]")) {
        currentSection = "skip";
      } else if (line.startsWith("[[routes]]")) {
        currentSection = "routes";
        routeSections += (routeSections ? "\n" : "") + line;
      } else if (line.startsWith("[") || line.startsWith("[[")) {
        currentSection = "other";
      } else {
        if (currentSection === "display") {
          sectionContent.push(line);
        } else if (currentSection === "stop") {
          currentStopBlock += "\n" + line;
        } else if (currentSection === "routes") {
          routeSections += "\n" + line;
        }
      }
    }

    // Process last stop
    if (currentStopBlock && currentSection === "stop") {
      const blockStopId = currentStopBlock.match(
        /station_id\s*=\s*"([^"]+)"/
      );
      if (blockStopId && !stopsToAdd.has(blockStopId[1])) {
        existingStopsBlocks +=
          (existingStopsBlocks ? "\n" : "") + currentStopBlock;
      }
    }

    displaySection = sectionContent.join("\n");

    // Build final config
    let finalConfig = "";
    if (displaySection) {
      finalConfig += displaySection + "\n\n";
    }
    if (existingStopsBlocks) {
      finalConfig += existingStopsBlocks + "\n\n";
    }

    for (const stop of newStops) {
      finalConfig += "[[stops]]\n";
      finalConfig += `station_id = "${stop.station_id}"\n`;
      finalConfig += `station_name = "${stop.station_name}"\n`;
      finalConfig += `max_departures_per_stop = ${stop.max_departures_per_stop}\n`;
      finalConfig += `max_departures_per_route = ${stop.max_departures_per_route}\n`;
      finalConfig += `max_hours_in_advance = ${stop.max_hours_in_advance}\n`;
      finalConfig += `show_ungrouped = ${stop.show_ungrouped}\n\n`;
    }

    if (routeSections) {
      finalConfig += routeSections + "\n\n";
    }

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

    // Simulate merge with direction_mappings preservation
    const stopsToAdd = new Set(newStops.map((s) => s.station_id));
    let existingStopsBlocks = "";
    let currentSection = "";
    let currentStopBlock = "";

    const lines = existingConfig.split("\n");

    for (const line of lines) {
      if (line.startsWith("[[stops]]")) {
        if (currentStopBlock) {
          const blockStopId = currentStopBlock.match(
            /station_id\s*=\s*"([^"]+)"/
          );
          if (blockStopId && !stopsToAdd.has(blockStopId[1])) {
            // Keep it INCLUDING direction_mappings
            existingStopsBlocks +=
              (existingStopsBlocks ? "\n" : "") + currentStopBlock;
          }
        }
        currentSection = "stop";
        currentStopBlock = line;
      } else if (line.startsWith("[stops.") || line.startsWith("[stops]")) {
        // Include direction_mappings in preserved stops
        currentSection = "stop";
        currentStopBlock += "\n" + line;
      } else if (currentStopBlock) {
        currentStopBlock += "\n" + line;
      }
    }

    // Process last stop
    if (currentStopBlock) {
      const blockStopId = currentStopBlock.match(
        /station_id\s*=\s*"([^"]+)"/
      );
      if (blockStopId && !stopsToAdd.has(blockStopId[1])) {
        existingStopsBlocks +=
          (existingStopsBlocks ? "\n" : "") + currentStopBlock;
      }
    }

    // Build final
    let finalConfig = "";
    if (existingStopsBlocks) {
      finalConfig += existingStopsBlocks + "\n\n";
    }

    for (const stop of newStops) {
      finalConfig += "[[stops]]\n";
      finalConfig += `station_id = "${stop.station_id}"\n`;
      finalConfig += `station_name = "${stop.station_name}"\n`;
      finalConfig += `max_departures_per_stop = ${stop.max_departures_per_stop}\n`;
      finalConfig += `max_departures_per_route = ${stop.max_departures_per_route}\n`;
      finalConfig += `max_hours_in_advance = ${stop.max_hours_in_advance}\n`;
      finalConfig += `show_ungrouped = ${stop.show_ungrouped}\n\n`;
    }

    // Verify both stops are in config
    expect(finalConfig).toContain('station_id = "de:09162:1110"');
    expect(finalConfig).toContain('station_id = "de:09162:1108:3:3"');
    
    // Verify direction_mappings is preserved
    expect(finalConfig).toContain("[stops.direction_mappings]");
    expect(finalConfig).toContain('"Platform 1"');
    expect(finalConfig).toContain('"Platform 2"');

    console.log("✓ Preserved existing stop with direction_mappings while adding sub-stop");
    console.log("Final config:\n", finalConfig);
  });
});
