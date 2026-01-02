// VVO Iframe Fallback - JavaScript
// This file can be used for any dynamic behavior if needed

(function ($) {
  "use strict";

  const BASE_LINES = 2; // Base lines (header + table header)

  // Extract limit parameter from VVO URL
  // URL pattern: /en/dm/0/0075bf/fff/{leadtime}/{limit}/{stopid}
  function extractLimit(url) {
    const match = url.match(/\/en\/dm\/0\/0075bf\/fff\/\d+\/(\d+)\/\d+/);
    return match ? parseInt(match[1], 10) : null;
  }

  // Calculate proportional heights based on number of lines (limit parameter)
  function adjustIframeHeights() {
    const containers = $(".iframe-container");
    const lineCounts = [];
    let totalLines = 0;

    // Calculate total lines for each iframe (base + limit)
    containers.each(function () {
      const $iframe = $(this).find("iframe");
      const src = $iframe.attr("src");
      const limit = extractLimit(src);

      if (limit !== null) {
        const totalLinesForIframe = BASE_LINES + limit;
        lineCounts.push(totalLinesForIframe);
        totalLines += totalLinesForIframe;
      } else {
        const defaultLines = BASE_LINES + 5;
        lineCounts.push(defaultLines);
        totalLines += defaultLines;
      }
    });

    // Apply proportional heights using flex-basis
    containers.each(function (index) {
      const lines = lineCounts[index];
      const heightPercent = totalLines > 0 ? (lines / totalLines) * 100 : 100 / containers.length;

      $(this).css({
        flex: "0 0 " + heightPercent + "%",
      });
    });
  }

  // Adjust on load and resize
  $(document).ready(function () {
    adjustIframeHeights();
  });

  $(window).on("resize", function () {
    adjustIframeHeights();
  });

  // Recalculate after iframes load
  $("iframe").on("load", function () {
    setTimeout(adjustIframeHeights, 100);
  });
})(jQuery);
