/**
 * Initialize destination scrolling for clipped text
 * Ported from static/js/app.js
 */

export function initDestinationScrolling(): void {
  const destinations = document.querySelectorAll(".destination-text");
  console.log(`[destination-scrolling] Checking ${destinations.length} destinations`);
  
  destinations.forEach((textEl, index) => {
    // Type guard: ensure textEl is HTMLElement to access style property
    if (!(textEl instanceof HTMLElement)) {
      return;
    }

    const container = textEl.closest(".destination");
    if (!container || !(container instanceof HTMLElement)) return;
    
    const routeContainer = container.closest(".route-container");
    if (!routeContainer || !(routeContainer instanceof HTMLElement)) return;
    
    const departureRow = container.closest(".departure-row");
    if (!departureRow || !(departureRow instanceof HTMLElement)) return;

    // Force layout recalculation
    departureRow.getBoundingClientRect();
    routeContainer.getBoundingClientRect();
    container.getBoundingClientRect();
    textEl.getBoundingClientRect();

    // Get the actual rendered widths
    const textScrollWidth = textEl.scrollWidth;
    const textOffsetWidth = textEl.offsetWidth;
    const containerClientWidth = container.clientWidth;
    const containerOffsetWidth = container.offsetWidth;
    const routeContainerClientWidth = routeContainer.clientWidth;
    const routeContainerOffsetWidth = routeContainer.offsetWidth;
    const departureRowClientWidth = departureRow.clientWidth;
    
    // Calculate available space for destination in the grid
    // The route-container is a grid with: route-number column + destination column (1fr)
    const routeNumber = routeContainer.querySelector(".route-number");
    const routeNumberWidth = routeNumber instanceof HTMLElement ? routeNumber.offsetWidth : 0;
    const gap = 0.3 * 16; // 0.3em gap in pixels (assuming 16px base)
    const availableDestinationWidth = routeContainerClientWidth - routeNumberWidth - gap;
    
    const wasClipped = textEl.classList.contains("clipped");
    
    // Text is clipped if it's wider than the available space in the grid column
    // Even if the container expands, we check against the actual available space
    const isClipped = textScrollWidth > availableDestinationWidth;

    console.log(`[destination-scrolling] Destination ${index}: textScroll=${textScrollWidth}, availableWidth=${availableDestinationWidth}, routeContainerWidth=${routeContainerClientWidth}, routeNumberWidth=${routeNumberWidth}, isClipped=${isClipped}, text="${textEl.textContent?.substring(0, 20)}..."`);

    if (isClipped) {
      // Text is clipped - add clipped class and calculate exact scroll distance
      // Negative because we need to scroll left (text is wider than available space)
      const scrollDistance = availableDestinationWidth - textScrollWidth;
      const currentScrollDistance =
        textEl.style.getPropertyValue("--scroll-distance");

      // Only update if clipping state changed or scroll distance changed significantly
      // This prevents restarting animation unnecessarily when time format changes
      if (
        !wasClipped ||
        Math.abs(parseFloat(currentScrollDistance) - scrollDistance) > 1
      ) {
        console.log(`[destination-scrolling] Adding clipped class to destination ${index}, scrollDistance=${scrollDistance}px`);
        textEl.classList.add("clipped");
        // Set CSS variable with the exact scroll distance
        textEl.style.setProperty("--scroll-distance", scrollDistance + "px");
        // Verify it was set
        const verifyDistance = textEl.style.getPropertyValue("--scroll-distance");
        const hasClippedClass = textEl.classList.contains("clipped");
        console.log(`[destination-scrolling] Verified: hasClippedClass=${hasClippedClass}, --scroll-distance=${verifyDistance}`);
      } else {
        console.log(`[destination-scrolling] Destination ${index} already clipped, skipping update`);
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
