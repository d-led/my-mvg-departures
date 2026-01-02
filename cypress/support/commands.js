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
