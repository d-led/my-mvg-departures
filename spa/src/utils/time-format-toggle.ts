/**
 * Time format toggle utility - ported from static/js/app.js
 * Handles animation between relative and absolute time formats
 */

let timeFormatToggleInterval: number | null = null;
let currentTimeFormat: "relative" | "absolute" = "relative";

export function initTimeFormatToggle(
  timeFormatToggleSeconds: number = 0,
): void {
  // Clear any existing interval
  if (timeFormatToggleInterval !== null) {
    clearInterval(timeFormatToggleInterval);
    timeFormatToggleInterval = null;
  }

  // Ensure all time elements start with relative format and full opacity
  document.querySelectorAll(".time").forEach((el) => {
    const container = el.closest(".time-container");
    if (!container) return;
    const relative = container.getAttribute("data-time-relative");
    if (relative) {
      // Preserve existing delay display if present
      const delayDisplay = el.querySelector(".delay-amount");
      const delayHTML = delayDisplay ? delayDisplay.outerHTML : "";
      el.innerHTML = relative + delayHTML;
    }
    (el as HTMLElement).style.opacity = "1";
  });

  if (timeFormatToggleSeconds > 0) {
    // Start with relative format
    currentTimeFormat = "relative";

    // Toggle every timeFormatToggleSeconds
    timeFormatToggleInterval = window.setInterval(
      () => toggleTimeFormat(),
      timeFormatToggleSeconds * 1000,
    );
  }
}

function toggleTimeFormat(): void {
  const timeElements = document.querySelectorAll(".time");

  timeElements.forEach((el) => {
    const container = el.closest(".time-container");
    if (!container) return;
    const relative = container.getAttribute("data-time-relative");
    const absolute = container.getAttribute("data-time-absolute");
    if (!relative || !absolute) return;

    const timeEl = el as HTMLElement;

    // Store current width to prevent layout shift when longer text is inserted
    const currentWidth = timeEl.offsetWidth;
    timeEl.style.width = currentWidth + "px";

    // Fade out smoothly
    timeEl.style.opacity = "0";

    setTimeout(() => {
      // Preserve delay display ONLY if it exists (i.e., when splitShowDelay is true)
      // When splitShowDelay is false (default), there is no delay indicator to preserve
      const delayDisplay = timeEl.querySelector(".delay-amount");
      const delayHTML = delayDisplay ? delayDisplay.outerHTML : "";

      // Change text content
      if (currentTimeFormat === "relative") {
        // Switch to absolute
        timeEl.innerHTML = absolute + delayHTML;
      } else {
        // Switch to relative
        timeEl.innerHTML = relative + delayHTML;
      }

      // Remove fixed width to allow new content to size naturally
      timeEl.style.width = "";

      // Fade in smoothly
      timeEl.style.opacity = "1";
    }, 150);
  });

  currentTimeFormat =
    currentTimeFormat === "relative" ? "absolute" : "relative";

  // Recalculate destination clipping after layout settles (time format change may affect container widths)
  setTimeout(() => {
    // Import dynamically to avoid circular dependency
    import("./destination-scrolling.js").then((module) => {
      module.initDestinationScrolling();
    });
  }, 200);
}

export function cleanupTimeFormatToggle(): void {
  if (timeFormatToggleInterval !== null) {
    clearInterval(timeFormatToggleInterval);
    timeFormatToggleInterval = null;
  }
}
