describe("MVG Departures Dashboard", () => {
  beforeEach(() => {
    cy.visit("/");
    cy.waitForConnection(30000);
  });

  it("should display the main header", () => {
    cy.shouldDisplayMainHeader();
  });

  it("should display at least one direction header", () => {
    cy.shouldDisplayDirectionHeaders();
  });

  it("should display the clock in the first header", () => {
    cy.shouldDisplayClock();
  });

  it("should display connection status indicator", () => {
    cy.shouldDisplayConnectionStatus();
  });

  it("should display API status indicator", () => {
    cy.shouldDisplayApiStatus();
  });

  it("should display refresh countdown timer", () => {
    cy.shouldDisplayRefreshCountdown();
  });

  it("should display presence count indicator", () => {
    cy.shouldDisplayPresenceCount();
  });

  it("should display departure information when available", () => {
    cy.shouldDisplayDepartureInformation();
  });

  it("should have accessible ARIA labels", () => {
    cy.shouldHaveAccessibleAriaLabels();
  });

  it("should display status floating box with all indicators", () => {
    cy.shouldDisplayStatusFloatingBox();
  });
});
