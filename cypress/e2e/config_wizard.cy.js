describe('Configuration Wizard', () => {
  beforeEach(() => {
    // Start the app on the 'Next to me' route
    cy.visit('/#on-the-run');
    cy.waitForConnection(30000);
  });

  it("does not offer to configure the current route when on-the-run", () => {
    // Open configuration modal
    cy.get('.status-floating-box .config-button').click();
    cy.get('.modal-overlay').should('be.visible');

    // Open the wizard
    cy.contains('button', 'Wizard (experimental)').click();

    // Wizard should be visible
    cy.get('.wizard-content').should('be.visible');

    // Assert: 'Current Route' option is NOT present
    cy.contains('.wizard-content', 'Current Route').should('not.exist');
  });
});
