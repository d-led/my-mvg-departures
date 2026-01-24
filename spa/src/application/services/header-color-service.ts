import type { GroupedDepartures } from "../../domain/models/grouped-departures.js";
import type { DisplayConfiguration } from "../../domain/models/route-configuration.js";
import md5 from "md5";

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
      const directionClean = group.directionName.replace(/^->/, "");
      const headerText = `${group.stopName} → ${directionClean}`;
      group.headerColor = generatePastelColor(headerText, brightness, salt);
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

function generatePastelColor(
  text: string,
  brightness: number = 0.7,
  salt: number = 0,
): string {
  const str = `${text}:${salt}`;
  const md5Hex = md5(str);
  const hashBigInt = BigInt("0x" + md5Hex);

  const hashPart1 = Number((hashBigInt >> 16n) & 0xffffn);
  const hashPart2 = Number(hashBigInt & 0xffffn);

  const hueBase = hashPart1 % 360;
  const hueVariation = (hashPart2 % 60) - 30;
  const hue = (hueBase + hueVariation) % 360;

  const hashInt = Number(hashBigInt & 0xffffffffffffffffn);
  const saturation = 55 + (hashInt % 26);

  const brightnessAdjusted = Math.pow(brightness, 1.5);
  const baseLightnessMin = 30 + brightnessAdjusted * 45;
  const baseLightnessMax = 40 + brightnessAdjusted * 45;
  const lightnessRange = Math.max(1, baseLightnessMax - baseLightnessMin);
  const lightness = baseLightnessMin + (hashInt % lightnessRange);

  const h = hue / 360;
  const s = saturation / 100;
  const l = lightness / 100;

  const c = (1 - Math.abs(2 * l - 1)) * s;
  const x = c * (1 - Math.abs(((h * 6) % 2) - 1));
  const m = l - c / 2;

  let r = 0,
    g = 0,
    b = 0;
  if (h < 1 / 6) {
    r = c;
    g = x;
    b = 0;
  } else if (h < 2 / 6) {
    r = x;
    g = c;
    b = 0;
  } else if (h < 3 / 6) {
    r = 0;
    g = c;
    b = x;
  } else if (h < 4 / 6) {
    r = 0;
    g = x;
    b = c;
  } else if (h < 5 / 6) {
    r = x;
    g = 0;
    b = c;
  } else {
    r = c;
    g = 0;
    b = x;
  }

  r = Math.round((r + m) * 255);
  g = Math.round((g + m) * 255);
  b = Math.round((b + m) * 255);

  return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
}
