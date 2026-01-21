/**
 * Initialize destination scrolling for clipped text
 * Ported from static/js/app.js
 */

export function initDestinationScrolling(): void {
  document.querySelectorAll(".destination-text").forEach((textEl) => {
    const container = textEl.closest(".destination");
    if (!container) return;
    
    // Check if text is clipped (text width > container width)
    const textWidth = textEl.scrollWidth;
    const containerWidth = container.clientWidth;
    const wasClipped = textEl.classList.contains("clipped");
    const isClipped = textWidth > containerWidth;

    if (isClipped) {
      // Text is clipped - add clipped class and calculate exact scroll distance
      const scrollDistance = containerWidth - textWidth;
      const currentScrollDistance = textEl.style.getPropertyValue("--scroll-distance");

      // Only update if clipping state changed or scroll distance changed significantly
      // This prevents restarting animation unnecessarily when time format changes
      if (!wasClipped || Math.abs(parseFloat(currentScrollDistance) - scrollDistance) > 1) {
        textEl.classList.add("clipped");
        // Set CSS variable with the exact scroll distance
        textEl.style.setProperty("--scroll-distance", scrollDistance + "px");
      }
    } else {
      // Text fits - remove clipped class
      if (wasClipped) {
        textEl.classList.remove("clipped");
        textEl.style.removeProperty("--scroll-distance");
      }
    }
  });
}
