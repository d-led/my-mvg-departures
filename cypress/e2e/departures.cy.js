describe("MVG Departures Dashboard", () => {
  beforeEach(() => {
    cy.visit("/");
    // Wait for the page to load and WebSocket connection to establish
    cy.waitForConnection(30000);
  });

  it("should display the main header", () => {
    cy.get("h1").should("contain", "MVG Departures");
  });

  it("should display at least one direction header", () => {
    // Wait for departures to load
    cy.get("#departures", { timeout: 10000 }).should("be.visible");
    // Check that at least one direction header exists
    cy.get(".direction-header").should("have.length.at.least", 1);
  });

  it("should display the clock in the first header", () => {
    cy.get("#departures", { timeout: 10000 }).should("be.visible");
    // The clock should be in the first header with id datetime-display
    // It only exists if there are departures with a first header
    // Check if clock exists, and if so, verify it has content
    cy.get("body").then(($body) => {
      const clockExists = $body.find("#datetime-display").length > 0;
      if (clockExists) {
        // Wait for it to have content (updated by JavaScript on page load)
        cy.get("#datetime-display", { timeout: 3000 })
          .should("be.visible")
          .should(($el) => {
            const text = $el.text().trim();
            // Either matches time format (HH:MM) or full date-time (YYYY-MM-DD HH:MM)
            expect(text.length).to.be.greaterThan(0);
            expect(text).to.match(/\d{1,2}:\d{2}/);
          });
      } else {
        // If no clock exists (no departures), that's acceptable
        cy.log("No clock element - no departures available");
      }
    });
  });

  it("should display connection status indicator", () => {
    cy.get("#connection-status").should("be.visible");
    // Should have one of the connection state icons
    cy.get("#connection-status").within(() => {
      cy.get("img").should("have.length.at.least", 1);
    });
  });

  it("should display API status indicator", () => {
    cy.get("#api-status-container").should("be.visible");
    // Should have one of the API status icons
    cy.get("#api-status-container").within(() => {
      cy.get("svg").should("have.length.at.least", 1);
    });
  });

  it("should display refresh countdown timer", () => {
    cy.get(".refresh-countdown").should("be.visible");
    cy.get(".refresh-countdown svg").should("be.visible");
  });

  it("should display presence count indicator", () => {
    cy.get("#presence-count").should("be.visible");
    cy.get("#presence-count .presence-icon").should("be.visible");
  });

  it("should display departure information when available", () => {
    cy.get("#departures", { timeout: 10000 }).should("be.visible");

    // Check if there are departures or a "no departures" message
    cy.get("#departures").within(() => {
      // Either we have departure rows or a no departures message
      cy.get(".departure-row, [role='status']").should("have.length.at.least", 1);
    });
  });

  it("should have accessible ARIA labels", () => {
    cy.get("#departures").should("have.attr", "role", "region");
    cy.get("#departures").should("have.attr", "aria-label");
    cy.get("#aria-live-status").should("exist");
    cy.get("#aria-live-departures").should("exist");
  });

  it("should display status floating box with all indicators", () => {
    cy.get(".status-floating-box").should("be.visible");
    // Should contain connection status, API status, refresh countdown, and presence
    cy.get(".status-floating-box-item").should("have.length.at.least", 3);
  });
});
