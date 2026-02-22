import type { GroupedDepartures } from "../../domain/models/grouped-departures.js";
import type { DisplayConfiguration } from "../../domain/models/route-configuration.js";
import { generatePastelColorFromText } from "../../utils/color-from-hash.js";

export function generateHeaderColors(
  groups: GroupedDepartures[],
  routeDisplay?: DisplayConfiguration,
): void {
  console.log(
    `[header-colors] Generating colors for ${groups.length} groups, routeDisplay.randomHeaderColors=${routeDisplay?.randomHeaderColors}, routeDisplay.headerBackgroundBrightness=${routeDisplay?.headerBackgroundBrightness}`,
  );

  for (let i = 1; i < groups.length; i++) {
    const group = groups[i];

    const useRandomColors =
      group.randomHeaderColors !== undefined &&
      group.randomHeaderColors !== null
        ? group.randomHeaderColors
        : (routeDisplay?.randomHeaderColors ?? false);
    const brightness =
      group.headerBackgroundBrightness !== undefined &&
      group.headerBackgroundBrightness !== null
        ? group.headerBackgroundBrightness
        : (routeDisplay?.headerBackgroundBrightness ?? 0.7);
    const salt =
      group.randomColorSalt !== undefined && group.randomColorSalt !== null
        ? group.randomColorSalt
        : 0;

    console.log(
      `[header-colors] Group ${i} (${group.stopName} [${group.stationId}] → ${group.directionName}): group.randomHeaderColors=${group.randomHeaderColors}, useRandomColors=${useRandomColors}, brightness=${brightness}, salt=${salt}`,
    );

    if (useRandomColors) {
      const directionClean = String(group.directionName ?? "").replace(
        /^->/,
        "",
      );
      const headerText = `${group.stopName} → ${directionClean}`;
      group.headerColor = generatePastelColorFromText(
        headerText,
        brightness,
        salt,
      );
      console.log(
        `[header-colors] Generated color for group ${i}: ${group.headerColor}`,
      );
    } else {
      group.headerColor = undefined;
      console.log(
        `[header-colors] Not generating color for group ${i} (random_header_colors disabled)`,
      );
    }
  }
}
