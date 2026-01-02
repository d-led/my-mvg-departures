// ***********************************************
// This example commands.js shows you how to
// create various custom commands and overwrite
// existing commands.
//
// For more comprehensive examples of custom
// commands please read more here:
// https://on.cypress.io/custom-commands
// ***********************************************

/**
 * Wait for WebSocket connection to be established.
 * Checks the connection status indicator to ensure the app is connected.
 * @param {number} timeout - Timeout in milliseconds (default: 30000)
 */
Cypress.Commands.add("waitForConnection", (timeout = 30000) => {
  // Wait for the connection status element to exist
  cy.get("#connection-status", { timeout }).should("exist");

  // Wait for connection to be established by checking the data-connection-state attribute
  // It should change from "connecting" to "connected"
  cy.get("#connection-status", { timeout }).should(($el) => {
    const connectionState = $el.attr("data-connection-state");
    if (connectionState !== "connected") {
      throw new Error(`Connection not established. Current state: ${connectionState || "unknown"}`);
    }
  });

  // Also verify the connected icon is visible as a secondary check
  cy.get("#connection-status #connected-icon", { timeout }).should("be.visible");
});

/**
 * Wait for the departures section to be visible.
 * @param {number} timeout - Timeout in milliseconds (default: 10000)
 */
Cypress.Commands.add("waitForDepartures", (timeout = 10000) => {
  cy.get("#departures", { timeout }).should("be.visible");
});

/**
 * Assert that the main header displays the expected text.
 * @param {string} expectedText - Expected text in the header (default: "MVG Departures")
 */
Cypress.Commands.add("shouldDisplayMainHeader", (expectedText = "Departures") => {
  cy.get("h1").should("contain", expectedText);
});

/**
 * Assert that at least the minimum number of direction headers are displayed.
 * @param {number} minCount - Minimum number of direction headers (default: 1)
 * @param {number} timeout - Timeout in milliseconds (default: 10000)
 */
Cypress.Commands.add("shouldDisplayDirectionHeaders", (minCount = 1, timeout = 10000) => {
  cy.waitForDepartures(timeout);
  cy.get(".direction-header").should("have.length.at.least", minCount);
});

/**
 * Assert that the clock is displayed in the first header when departures are available.
 * If no clock exists (no departures), logs that this is acceptable.
 * @param {number} timeout - Timeout in milliseconds (default: 10000)
 */
Cypress.Commands.add("shouldDisplayClock", (timeout = 10000) => {
  cy.waitForDepartures(timeout);
  cy.get("body").then(($body) => {
    const clockExists = $body.find("#datetime-display").length > 0;
    if (clockExists) {
      cy.get("#datetime-display", { timeout: 3000 })
        .should("be.visible")
        .should(($el) => {
          const text = $el.text().trim();
          expect(text.length).to.be.greaterThan(0);
          expect(text).to.match(/\d{1,2}:\d{2}/);
        });
    } else {
      cy.log("No clock element - no departures available");
    }
  });
});

/**
 * Assert that the connection status indicator is visible with an icon.
 */
Cypress.Commands.add("shouldDisplayConnectionStatus", () => {
  cy.get("#connection-status").should("be.visible");
  cy.get("#connection-status").within(() => {
    cy.get("img").should("have.length.at.least", 1);
  });
});

/**
 * Assert that the API status indicator is visible with an icon.
 */
Cypress.Commands.add("shouldDisplayApiStatus", () => {
  cy.get("#api-status-container").should("be.visible");
  cy.get("#api-status-container").within(() => {
    cy.get("svg").should("have.length.at.least", 1);
  });
});

/**
 * Assert that the refresh countdown timer is visible.
 */
Cypress.Commands.add("shouldDisplayRefreshCountdown", () => {
  cy.get(".refresh-countdown").should("be.visible");
  cy.get(".refresh-countdown svg").should("be.visible");
});

/**
 * Assert that the presence count indicator is visible.
 */
Cypress.Commands.add("shouldDisplayPresenceCount", () => {
  cy.get("#presence-count").should("be.visible");
  cy.get("#presence-count .presence-icon").should("be.visible");
});

/**
 * Assert that departure information is displayed when available.
 * Either departure rows or a "no departures" message should be present.
 * @param {number} timeout - Timeout in milliseconds (default: 10000)
 */
Cypress.Commands.add("shouldDisplayDepartureInformation", (timeout = 10000) => {
  cy.waitForDepartures(timeout);
  cy.get("#departures").within(() => {
    cy.get(".departure-row, [role='status']").should("have.length.at.least", 1);
  });
});

/**
 * Assert that the page has accessible ARIA labels.
 */
Cypress.Commands.add("shouldHaveAccessibleAriaLabels", () => {
  cy.get("#departures").should("have.attr", "role", "region");
  cy.get("#departures").should("have.attr", "aria-label");
  cy.get("#aria-live-status").should("exist");
  cy.get("#aria-live-departures").should("exist");
});

/**
 * Assert that the status floating box is visible with all indicators.
 * @param {number} minItems - Minimum number of status items (default: 3)
 */
Cypress.Commands.add("shouldDisplayStatusFloatingBox", (minItems = 3) => {
  cy.get(".status-floating-box").should("be.visible");
  cy.get(".status-floating-box-item").should("have.length.at.least", minItems);
});
