/**
 * Dynamic font scaling utility - ported from static/js/app.js
 * Calculates font sizes to fill vertical space when fillVerticalSpace is enabled
 */

export interface FontScalingConfig {
  fillVerticalSpace?: boolean;
  fontScalingFactorWhenFilling?: number;
}

/**
 * Set font sizes from config values (when fillVerticalSpace is disabled)
 * This ensures proper font sizes and line-heights to prevent overlap
 */
export function setFontSizesFromConfig(display?: {
  fontSizeRouteNumber?: string;
  fontSizeDestination?: string;
  fontSizePlatform?: string;
  fontSizeTime?: string;
  fontSizeDirectionHeader?: string;
  fontSizeStopHeader?: string;
  fontSizeNoDepartures?: string;
  fontSizePaginationIndicator?: string;
  fontSizeCountdownText?: string;
  fontSizeDelayAmount?: string;
  fontSizeStatusHeader?: string;
}): void {
  const root = document.documentElement;

  // Set font sizes from config (if provided), otherwise use defaults
  // Convert rem to px based on root font size (typically 16px)
  const rootFontSize = parseFloat(getComputedStyle(root).fontSize) || 16;

  const remToPx = (rem: string | undefined, defaultRem: number): number => {
    if (!rem) return defaultRem * rootFontSize;
    const remValue = parseFloat(rem.replace("rem", ""));
    return isNaN(remValue)
      ? defaultRem * rootFontSize
      : remValue * rootFontSize;
  };

  root.style.setProperty(
    "--font-size-route-number",
    display?.fontSizeRouteNumber || "4rem",
  );
  root.style.setProperty(
    "--font-size-destination",
    display?.fontSizeDestination || "4rem",
  );
  root.style.setProperty(
    "--font-size-platform",
    display?.fontSizePlatform || "2.5rem",
  );
  root.style.setProperty("--font-size-time", display?.fontSizeTime || "4rem");
  root.style.setProperty(
    "--font-size-direction-header",
    display?.fontSizeDirectionHeader || "2.5rem",
  );
  root.style.setProperty(
    "--font-size-stop-header",
    display?.fontSizeStopHeader || "3rem",
  );
  root.style.setProperty(
    "--font-size-no-departures",
    display?.fontSizeNoDepartures || "2.5rem",
  );
  root.style.setProperty(
    "--font-size-pagination-indicator",
    display?.fontSizePaginationIndicator || "2rem",
  );
  root.style.setProperty(
    "--font-size-countdown-text",
    display?.fontSizeCountdownText || "1.8rem",
  );
  root.style.setProperty(
    "--font-size-delay-amount",
    display?.fontSizeDelayAmount || "2rem",
  );
  root.style.setProperty(
    "--font-size-status-header",
    display?.fontSizeStatusHeader || "1.875rem",
  );

  // Ensure proper line-heights to prevent overlap (matches Python CSS: line-height: 1.2)
  root.style.setProperty("--line-height", "1.2");

  // Calculate column widths dynamically (same as fillVerticalSpace mode)
  const departuresEl = document.getElementById("departures");
  if (!departuresEl) return;

  // Get font sizes in px for width calculations
  const routeNumberPx = remToPx(display?.fontSizeRouteNumber, 4);
  const platformPx = remToPx(display?.fontSizePlatform, 2.5);
  const timePx = remToPx(display?.fontSizeTime, 4);

  // Temporarily set auto widths to allow content measurement
  root.style.setProperty("--route-column-width", "auto");
  root.style.setProperty("--time-container-width", "auto");
  root.style.setProperty("--platform-column-width", "auto");
  root.style.setProperty("--time-column-width", "auto");

  // Force reflow to ensure CSS variables are applied to elements
  void departuresEl.offsetHeight;

  // Force another reflow to ensure fonts are rendered with the new sizes
  // This is critical on first load when fonts might not be applied yet
  const firstRouteNumber = departuresEl.querySelector(".route-number");
  if (firstRouteNumber) {
    void (firstRouteNumber as HTMLElement).offsetHeight;
  }

  // Measure route numbers
  let maxRouteWidth = 0;
  const routeNumbers = departuresEl.querySelectorAll(".route-number");
  routeNumbers.forEach((el) => {
    const width = (el as HTMLElement).scrollWidth;
    if (width > maxRouteWidth) maxRouteWidth = width;
  });
  let routeColumnWidth = Math.max(
    maxRouteWidth + routeNumberPx * 0.3,
    routeNumberPx * 2.5,
  );
  const maxRouteColPx = departuresEl.clientWidth * 0.45;
  if (routeColumnWidth > maxRouteColPx) routeColumnWidth = maxRouteColPx;
  root.style.setProperty("--route-column-width", routeColumnWidth + "px");

  // Measure platforms
  let maxPlatformWidth = 0;
  const platforms = departuresEl.querySelectorAll(".time-container .platform");
  platforms.forEach((el) => {
    const width = (el as HTMLElement).scrollWidth;
    if (width > maxPlatformWidth) maxPlatformWidth = width;
  });
  const platformColumnWidth =
    maxPlatformWidth > 0 ? maxPlatformWidth + platformPx * 0.3 : 0;
  root.style.setProperty(
    "--platform-column-width",
    platformColumnWidth > 0 ? platformColumnWidth + "px" : "0px",
  );

  // Measure times
  let maxTimeWidth = 0;
  const times = departuresEl.querySelectorAll(".time-container .time");
  times.forEach((el) => {
    const width = (el as HTMLElement).scrollWidth;
    if (width > maxTimeWidth) maxTimeWidth = width;
  });
  const timeColumnWidth = maxTimeWidth + timePx * 0.3;
  root.style.setProperty("--time-column-width", timeColumnWidth + "px");

  // Calculate time container width
  const timeContainerGap = timePx * 0.2;
  root.style.setProperty("--time-container-gap", timeContainerGap + "px");
  const containerPadding = 12;
  const effectiveGap = platformColumnWidth > 0 ? timeContainerGap : 0;
  const timeContainerWidth =
    platformColumnWidth + effectiveGap + timeColumnWidth + containerPadding * 2;
  root.style.setProperty("--time-container-width", timeContainerWidth + "px");

  // Ensure proper line-heights on elements to prevent overlap
  const departureRows = departuresEl.querySelectorAll(".departure-row");
  departureRows.forEach((row) => {
    const r = row as HTMLElement;
    r.style.lineHeight = "1.2"; // Match body line-height
  });

  const directionHeaders = departuresEl.querySelectorAll(".direction-header");
  directionHeaders.forEach((header) => {
    const h = header as HTMLElement;
    h.style.lineHeight = "1.2"; // Match body line-height
  });
}

export function calculateFillVerticalSpace(config: FontScalingConfig): void {
  if (!config.fillVerticalSpace) {
    console.log(
      "[font-scaling] fillVerticalSpace is false, skipping calculation",
    );
    return;
  }

  console.log("[font-scaling] Starting calculateFillVerticalSpace");
  const departuresEl = document.getElementById("departures");
  if (!departuresEl) {
    console.warn("[font-scaling] departures element not found");
    return;
  }

  // Get all direction groups
  const directionGroups = departuresEl.querySelectorAll(".direction-group");
  if (directionGroups.length === 0) return;

  // Count total rows: each direction group has 1 header + its departure rows
  let totalRows = 0;
  directionGroups.forEach((group) => {
    const header = group.querySelector(".direction-header");
    const departureRows = group.querySelectorAll(".departure-row");
    if (header) totalRows += 1; // Header counts as 1 row
    totalRows += departureRows.length;
  });

  if (totalRows === 0) return;

  // Calculate available viewport height more accurately
  // Measure the actual status bar height from the DOM
  const statusBar = document.querySelector(".status-floating-box");
  let statusBarHeight = 60; // Default fallback
  if (statusBar) {
    const rect = statusBar.getBoundingClientRect();
    // Get computed margin-bottom (status bar is at bottom: 1rem = ~16px)
    const computedStyle = window.getComputedStyle(statusBar);
    const marginBottom = parseFloat(computedStyle.marginBottom) || 16;
    statusBarHeight = rect.height + marginBottom;
  }

  const viewportHeight = window.innerHeight;
  // Use the full viewport height minus the actual status bar
  // Note: header-section is hidden via CSS (display: none) so it doesn't take up space
  const availableHeight = viewportHeight - statusBarHeight;

  console.log(
    `[font-scaling] viewportHeight=${viewportHeight}, statusBarHeight=${statusBarHeight}, availableHeight=${availableHeight}, totalRows=${totalRows}`,
  );

  // Calculate height per row, but cap it to maintain legibility
  // When there are few departures, we don't want to fill all vertical space with huge fonts
  const rootFontSize =
    parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;

  // Calculate what the height per row would be if we filled vertical space
  const calculatedHeightPerRow = availableHeight / totalRows;

  // Cap the row height to a reasonable maximum to prevent huge fonts with few departures
  // This translates to roughly 3.5rem maximum row height (56px at 16px root font)
  // This keeps the display compact and legible similar to the many-departure view
  const maxReasonableRowHeight = 3.5 * rootFontSize;
  const heightPerRow = Math.min(calculatedHeightPerRow, maxReasonableRowHeight);

  console.log(
    `[font-scaling] calculatedHeightPerRow=${calculatedHeightPerRow}px, cappedTo=${heightPerRow}px, totalRows=${totalRows}`,
  );

  // Use a stable, continuous fit formula: as totalRows increases, fit gets tighter
  // The fitFactor approaches 1.0 for many rows, and is more relaxed for few rows
  // Example: fitFactor = 0.92 + 0.08 * (1 - Math.tanh((totalRows-6)/8))
  // - For few rows (<=6), fitFactor ~1.0 (relaxed)
  // - For many rows (>=20), fitFactor ~0.92 (tight)
  const fitFactor = 0.92 + 0.08 * (1 - Math.tanh((totalRows - 6) / 8));
  const lineHeight = 1.25;
  const rowVerticalPaddingPx = 8; // 0.25rem top + 0.25rem bottom
  const maxFontFitsInRow =
    (heightPerRow - rowVerticalPaddingPx) / (lineHeight * fitFactor);

  // Reasonable max font sizes to keep display compact and legible like the many-departure view
  // Cap to 2rem for main elements (route, destination, time)
  const maxRouteDestinationTimePx = Math.min(
    maxFontFitsInRow,
    2 * rootFontSize,
  ); // 2rem cap for compact, legible display
  const maxHeaderFontPx = Math.min(maxFontFitsInRow, 1.5 * rootFontSize); // 1.5rem cap
  const maxPlatformPx = Math.min(maxFontFitsInRow, 1.5 * rootFontSize); // 1.5rem cap

  const reservedPadding = 0;
  const fontUsableHeight = heightPerRow - reservedPadding;
  const baseFontSize = fontUsableHeight / (lineHeight * fitFactor);

  // Calculate proportional font sizes (same ratios as before)
  const fontScalingFactor = config.fontScalingFactorWhenFilling || 1.0;

  const fontSizes = {
    routeNumber: baseFontSize * (4.0 / 3.5) * fontScalingFactor,
    destination: baseFontSize * (4.0 / 3.5) * fontScalingFactor,
    time: baseFontSize * (4.0 / 3.5) * fontScalingFactor,
    platform: baseFontSize * (2.5 / 3.5) * fontScalingFactor,
    directionHeader: baseFontSize * (4.0 / 3.5) * fontScalingFactor,
    stopHeader: baseFontSize * (3.0 / 3.5) * fontScalingFactor,
    noDepartures: baseFontSize * (2.5 / 3.5) * fontScalingFactor,
    paginationIndicator: baseFontSize * (2.0 / 3.5) * fontScalingFactor,
    countdownText: baseFontSize * (1.8 / 3.5) * fontScalingFactor,
    delayAmount: baseFontSize * (2.0 / 3.5) * fontScalingFactor,
    statusHeader: baseFontSize * (4.0 / 3.5) * fontScalingFactor,
  };

  // Cap so content fits in row and stays readable (no vertical/horizontal truncation)
  fontSizes.routeNumber = Math.min(
    fontSizes.routeNumber,
    maxRouteDestinationTimePx,
  );
  fontSizes.destination = Math.min(
    fontSizes.destination,
    maxRouteDestinationTimePx,
  );
  fontSizes.time = Math.min(fontSizes.time, maxRouteDestinationTimePx);
  fontSizes.platform = Math.min(fontSizes.platform, maxPlatformPx);
  fontSizes.directionHeader = Math.min(
    fontSizes.directionHeader,
    maxHeaderFontPx,
  );
  fontSizes.stopHeader = Math.min(fontSizes.stopHeader, maxHeaderFontPx);
  fontSizes.statusHeader = Math.min(fontSizes.statusHeader, maxHeaderFontPx);
  fontSizes.noDepartures = Math.min(fontSizes.noDepartures, maxPlatformPx);
  fontSizes.paginationIndicator = Math.min(
    fontSizes.paginationIndicator,
    maxPlatformPx,
  );
  fontSizes.countdownText = Math.min(fontSizes.countdownText, maxPlatformPx);
  fontSizes.delayAmount = Math.min(fontSizes.delayAmount, maxPlatformPx);

  // Apply minimum font size to ensure legibility (at least 12px)
  const minFontSize = 12;
  Object.keys(fontSizes).forEach((key) => {
    const k = key as keyof typeof fontSizes;
    if (fontSizes[k] < minFontSize) {
      fontSizes[k] = minFontSize;
    }
  });

  // Update CSS custom properties (use px units for precise control)
  const root = document.documentElement;
  root.style.setProperty(
    "--font-size-route-number",
    fontSizes.routeNumber + "px",
  );
  root.style.setProperty(
    "--font-size-destination",
    fontSizes.destination + "px",
  );
  root.style.setProperty("--font-size-platform", fontSizes.platform + "px");
  root.style.setProperty("--font-size-time", fontSizes.time + "px");
  root.style.setProperty(
    "--font-size-direction-header",
    fontSizes.directionHeader + "px",
  );
  root.style.setProperty(
    "--font-size-stop-header",
    fontSizes.stopHeader + "px",
  );
  root.style.setProperty(
    "--font-size-no-departures",
    fontSizes.noDepartures + "px",
  );
  root.style.setProperty(
    "--font-size-pagination-indicator",
    fontSizes.paginationIndicator + "px",
  );
  root.style.setProperty(
    "--font-size-countdown-text",
    fontSizes.countdownText + "px",
  );
  root.style.setProperty(
    "--font-size-delay-amount",
    fontSizes.delayAmount + "px",
  );
  root.style.setProperty(
    "--font-size-status-header",
    fontSizes.statusHeader + "px",
  );

  // Calculate time container gap (0.2em equivalent, scales with time font size)
  const timeContainerGap = fontSizes.time * 0.2;
  root.style.setProperty("--time-container-gap", timeContainerGap + "px");

  // Dynamically calculate column widths based on actual content
  // First, temporarily set auto widths to allow content measurement
  root.style.setProperty("--route-column-width", "auto");
  root.style.setProperty("--time-container-width", "auto");
  root.style.setProperty("--platform-column-width", "auto");
  root.style.setProperty("--time-column-width", "auto");

  // Force reflow to apply font sizes before measuring
  void departuresEl.offsetHeight;

  // Force another reflow to ensure fonts are rendered with the new sizes
  // This is critical on first load when fonts might not be applied yet
  const firstRouteNumber = departuresEl.querySelector(".route-number");
  if (firstRouteNumber) {
    void (firstRouteNumber as HTMLElement).offsetHeight;
  }

  // Measure the maximum width of route numbers (including badges/icons)
  let maxRouteWidth = 0;
  const routeNumbers = departuresEl.querySelectorAll(".route-number");
  routeNumbers.forEach((el) => {
    // Use scrollWidth to get full content width even if constrained
    const width = el.scrollWidth;
    if (width > maxRouteWidth) maxRouteWidth = width;
  });
  // Add padding (0.3em gap from grid) and ensure minimum width
  let routeColumnWidth = Math.max(
    maxRouteWidth + fontSizes.routeNumber * 0.3,
    fontSizes.routeNumber * 2.5,
  );
  const maxRouteColPx = departuresEl.clientWidth * 0.45;
  if (routeColumnWidth > maxRouteColPx) routeColumnWidth = maxRouteColPx;
  root.style.setProperty("--route-column-width", routeColumnWidth + "px");

  // Measure the maximum width of platforms
  let maxPlatformWidth = 0;
  const platforms = departuresEl.querySelectorAll(".time-container .platform");
  platforms.forEach((el) => {
    const width = el.scrollWidth;
    if (width > maxPlatformWidth) maxPlatformWidth = width;
  });
  // Add small padding for visual breathing room (only if there are platforms)
  const platformColumnWidth =
    maxPlatformWidth > 0 ? maxPlatformWidth + fontSizes.platform * 0.3 : 0;
  root.style.setProperty(
    "--platform-column-width",
    platformColumnWidth > 0 ? platformColumnWidth + "px" : "0px",
  );

  // Measure the maximum width of time elements (including delay amounts)
  let maxTimeWidth = 0;
  const times = departuresEl.querySelectorAll(".time-container .time");
  times.forEach((el) => {
    const width = el.scrollWidth;
    if (width > maxTimeWidth) maxTimeWidth = width;
  });
  // Add small padding for visual breathing room
  const timeColumnWidth = maxTimeWidth + fontSizes.time * 0.3;
  root.style.setProperty("--time-column-width", timeColumnWidth + "px");

  // Calculate total time container width: platform + gap (only if platform exists) + time + container padding
  const containerPadding = 12; // 0.75rem padding on each side (approximately 12px)
  const effectiveGap = platformColumnWidth > 0 ? timeContainerGap : 0;
  const timeContainerWidth =
    platformColumnWidth + effectiveGap + timeColumnWidth + containerPadding * 2;
  root.style.setProperty("--time-container-width", timeContainerWidth + "px");

  // Set line-height to match our calculation for better vertical space distribution
  root.style.setProperty("--line-height", lineHeight.toString());

  // Remove spurious margins from direction headers and set exact heights
  directionGroups.forEach((group) => {
    const header = group.querySelector(".direction-header") as HTMLElement;
    if (header) {
      // Remove top margin (0.5rem) that creates spurious space before headers
      header.style.marginTop = "0";
      header.style.marginBottom = "0";
      // Keep minimal symmetric padding for readability and vertical centering
      header.style.padding = "0 0.75rem";
      // Set exact height to match calculated row height
      header.style.height = heightPerRow + "px";
      header.style.minHeight = heightPerRow + "px";
      header.style.maxHeight = heightPerRow + "px";
      // Ensure flex alignment centers content vertically
      header.style.display = "flex";
      header.style.alignItems = "center";
      // Apply line-height to match our calculation
      header.style.lineHeight = lineHeight.toString();
    }
  });

  // Set exact heights on departure rows to eliminate extra spacing
  const departureRows = departuresEl.querySelectorAll(".departure-row");
  departureRows.forEach((row) => {
    const r = row as HTMLElement;
    // Set exact height (not just min-height) to ensure tight fit
    r.style.height = heightPerRow + "px";
    r.style.minHeight = heightPerRow + "px";
    r.style.maxHeight = heightPerRow + "px";
    // Keep minimal padding for readability (reduced from default)
    r.style.padding = "0.25rem 0 0.25rem 0.75rem";
    // Apply line-height to match our calculation for better vertical distribution
    r.style.lineHeight = lineHeight.toString();
  });

  // Remove any top margins from direction groups to eliminate spurious space
  directionGroups.forEach((group) => {
    const g = group as HTMLElement;
    g.style.marginTop = "0";
    g.style.marginBottom = "0";
  });

  // Ensure the departures container uses the full available height
  // This prevents any bottom whitespace from container padding/margins
  departuresEl.style.height = availableHeight + "px";
  departuresEl.style.maxHeight = availableHeight + "px";
  departuresEl.style.overflow = "hidden"; // Prevent scrolling since we're filling exactly

  console.log(
    `[font-scaling] Set departures container: height=${availableHeight}px, overflow=hidden`,
  );

  // Fit-first: cap direction/status header so all destination titles fit horizontally (no truncation)
  const fitUpperBound = fontSizes.directionHeader; // already capped by maxHeaderFontPx above
  const cappedDirectionHeader = capDirectionHeaderFontToFitAll(fitUpperBound);
  if (cappedDirectionHeader < fontSizes.directionHeader) {
    fontSizes.directionHeader = cappedDirectionHeader;
    fontSizes.statusHeader = cappedDirectionHeader;
    root.style.setProperty(
      "--font-size-direction-header",
      fontSizes.directionHeader + "px",
    );
    root.style.setProperty(
      "--font-size-status-header",
      fontSizes.statusHeader + "px",
    );
    console.log(
      `[font-scaling] Direction/status header set to ${cappedDirectionHeader}px to fit all titles`,
    );
  }

  // Scale any header text that still doesn't fit (safety net)
  scaleHeadersIfNeeded();

  console.log("[font-scaling] calculateFillVerticalSpace completed");
}

/**
 * Returns the maximum font size (px) that fits all direction header titles in their
 * current container width. Use this to cap header font so we fit titles instead of
 * maximizing to fill vertical space.
 */
function capDirectionHeaderFontToFitAll(currentHeaderFontPx: number): number {
  const departuresEl = document.getElementById("departures");
  if (!departuresEl) return currentHeaderFontPx;

  const headers = departuresEl.querySelectorAll(".direction-header");
  if (headers.length === 0) return currentHeaderFontPx;

  let minFitSize = currentHeaderFontPx;
  headers.forEach((header) => {
    const fitSize = getMaxFittingFontSizeForHeader(
      header as HTMLElement,
      currentHeaderFontPx,
    );
    if (fitSize < minFitSize) minFitSize = fitSize;
  });
  return minFitSize;
}

/**
 * For one direction header, returns the largest font size in [12, maxSizePx] that fits
 * the header text on one line within its current available width.
 */
function getMaxFittingFontSizeForHeader(
  header: HTMLElement,
  maxSizePx: number,
): number {
  let headerTextEl = header.querySelector(
    ".direction-header-text",
  ) as HTMLElement;
  if (!headerTextEl) headerTextEl = header;

  const clockEl = header.querySelector(".direction-header-time") as HTMLElement;
  const originalFontSize = headerTextEl.style.fontSize;
  const originalWhiteSpace = headerTextEl.style.whiteSpace;

  const minFontSize = 12;
  const searchMax = Math.max(minFontSize, Math.min(maxSizePx, 200)); // clamp for safety
  let minSize = minFontSize;
  let maxSize = searchMax;
  let bestSize = minFontSize;

  // Binary search for largest font size that fits on one line
  while (maxSize - minSize > 0.5) {
    const testSize = (minSize + maxSize) / 2;
    headerTextEl.style.fontSize = testSize + "px";
    headerTextEl.style.whiteSpace = "nowrap";
    if (clockEl) clockEl.style.fontSize = testSize + "px";
    void headerTextEl.offsetHeight;

    const fits = headerTextEl.scrollWidth <= headerTextEl.clientWidth;
    headerTextEl.style.whiteSpace = originalWhiteSpace;
    void headerTextEl.offsetHeight;

    if (!fits) {
      maxSize = testSize;
    } else {
      minSize = testSize;
      bestSize = testSize;
    }
  }

  headerTextEl.style.fontSize = originalFontSize;
  if (clockEl) clockEl.style.fontSize = "";
  return bestSize;
}

function scaleHeadersIfNeeded(): void {
  const departuresEl = document.getElementById("departures");
  if (!departuresEl) return;

  // Find all headers
  const headers = departuresEl.querySelectorAll(".direction-header");
  if (headers.length === 0) return;

  // Process each header
  headers.forEach((header) => {
    // Find the text element - could be .direction-header-text (first header) or the header itself
    let headerTextEl = header.querySelector(
      ".direction-header-text",
    ) as HTMLElement;
    if (!headerTextEl) {
      // For headers without .direction-header-text, use the header element itself
      headerTextEl = header as HTMLElement;
    }

    // Skip if no text element found
    if (!headerTextEl) return;

    // Find the clock element if it exists in this header
    const clockEl = header.querySelector(
      ".direction-header-time",
    ) as HTMLElement;

    // Reset any previous scaling to start fresh
    headerTextEl.style.fontSize = "";
    headerTextEl.style.whiteSpace = "";
    headerTextEl.style.overflow = "";
    headerTextEl.style.textOverflow = "";
    // Reset clock font size if it exists
    if (clockEl) {
      clockEl.style.fontSize = "";
    }

    // Force a reflow to get accurate measurements with default font size
    void headerTextEl.offsetHeight;

    // Get the computed font size
    const computedStyle = window.getComputedStyle(headerTextEl);
    const currentFontSize = parseFloat(computedStyle.fontSize);

    // Check if text is wrapping by temporarily setting white-space: nowrap
    const originalWhiteSpace = headerTextEl.style.whiteSpace;
    headerTextEl.style.whiteSpace = "nowrap";
    void headerTextEl.offsetHeight; // Force reflow

    const textNaturalWidth = headerTextEl.scrollWidth;
    const availableWidth = headerTextEl.clientWidth;

    // Restore original white-space
    headerTextEl.style.whiteSpace = originalWhiteSpace;
    void headerTextEl.offsetHeight; // Force reflow

    const isWrapping = textNaturalWidth > availableWidth;

    if (!isWrapping) {
      // Text fits on one line, no scaling needed
      return;
    }

    // Text is wrapping - scale it down until it fits
    // Use binary search for efficiency, with a minimum font size limit
    const minFontSize = 12; // Minimum readable font size
    let minSize = minFontSize;
    let maxSize = currentFontSize;
    let bestSize = minFontSize; // Start with minimum as fallback

    // Binary search to find the largest font size that fits on one line
    while (maxSize - minSize > 0.5) {
      const testSize = (minSize + maxSize) / 2;
      headerTextEl.style.fontSize = testSize + "px";
      headerTextEl.style.whiteSpace = "nowrap";
      // Apply same size to clock if it exists
      if (clockEl) {
        clockEl.style.fontSize = testSize + "px";
      }

      // Force a reflow to get accurate measurements
      void headerTextEl.offsetHeight;

      const textWidth = headerTextEl.scrollWidth;
      const containerWidth = headerTextEl.clientWidth;
      const fits = textWidth <= containerWidth;

      // Restore white-space after measurement
      headerTextEl.style.whiteSpace = originalWhiteSpace;
      void headerTextEl.offsetHeight;

      if (!fits) {
        maxSize = testSize;
      } else {
        minSize = testSize;
        bestSize = testSize;
      }
    }

    // Apply the best fitting size and ensure no wrapping
    headerTextEl.style.fontSize = bestSize + "px";
    headerTextEl.style.whiteSpace = "nowrap";
    // Apply same size to clock if it exists
    if (clockEl) {
      clockEl.style.fontSize = bestSize + "px";
    }
  });
}
