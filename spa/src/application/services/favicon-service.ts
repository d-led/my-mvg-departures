import { generatePastelColorFromText } from "../../utils/color-from-hash.js";

/**
 * Extract acronym from title: first letter of each word, up to 3 chars.
 * Matches pyview logic for 2 words; extends to support longer titles.
 */
function extractAcronym(title: string): string {
  const words = title.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "M";
  if (words.length === 1) return words[0][0].toUpperCase();
  return words
    .slice(0, 3)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
}

/**
 * Generate SVG favicon with acronym and hash-based background color.
 * Updates the document favicon link to use a data URL.
 */
export function updateFavicon(title: string): void {
  const acronym = extractAcronym(title);
  const bgColor = generatePastelColorFromText(title, 0.7, 0);
  const textColor = "#FFFFFF";

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect width="100" height="100" rx="15" fill="${bgColor}"/>
  <text x="50" y="50" font-family="sans-serif" font-size="52" font-weight="bold"
        fill="${textColor}" text-anchor="middle" dominant-baseline="central">${acronym}</text>
</svg>`;

  const dataUrl = `data:image/svg+xml,${encodeURIComponent(svg)}`;

  let link = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
  if (!link) {
    link = document.createElement("link");
    link.rel = "icon";
    link.type = "image/svg+xml";
    document.head.appendChild(link);
  }
  link.href = dataUrl;
}
