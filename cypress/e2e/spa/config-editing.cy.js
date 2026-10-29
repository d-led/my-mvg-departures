/**
 * The "Next to me" page is one optional TOML table. It is easy to lose by
 * accident (an editor that rewrote the file), so the configurator can put it
 * back - and never takes it away.
 *
 * The dialog's selectors and actions live in `cypress/support/commands.js`.
 */
const CONFIG_WITHOUT_ON_THE_RUN = `
[display]
title = "SPA e2e"

[[routes]]
path = "/"

[[routes.stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
show_ungrouped = true
`;

const CONFIG_WITH_ON_THE_RUN = `${CONFIG_WITHOUT_ON_THE_RUN}
[[on_the_run]]
radius_meters = 250
`;

describe("SPA config editing", () => {
  it("puts the Next to me page back into a config that lost it", () => {
    cy.openConfigDialog(CONFIG_WITHOUT_ON_THE_RUN);
    cy.openConfigurator();

    cy.nextToMeRow().should("contain", "missing");
    cy.restoreNextToMePage();
    cy.closeConfigurator();

    cy.tomlEditor().should("contain.value", "[[on_the_run]]");
    cy.configNotice().should("contain", "Next to me is back");

    cy.saveConfig();

    cy.storedConfig().should((saved) => {
      expect(saved).to.contain("[[on_the_run]]");
      expect(saved).to.contain("radius_meters = 50");
      expect(saved).to.contain("de:09162:1110");
    });
  });

  it("asks before throwing unsaved edits away", () => {
    cy.openConfigDialog(CONFIG_WITHOUT_ON_THE_RUN);

    // Nothing edited yet: Cancel just closes.
    cy.cancelConfigDialog();

    cy.openConfigDialog(CONFIG_WITHOUT_ON_THE_RUN);
    cy.openConfigurator();
    cy.restoreNextToMePage();
    cy.closeConfigurator();

    cy.cancelConfigDialog();
    cy.keepEditing();

    cy.openConfigurator();
    cy.nextToMeRow().should("contain", "in this config");
    cy.closeConfigurator();

    cy.cancelConfigDialog();
    cy.discardChanges();

    cy.storedConfig().should("not.contain", "[[on_the_run]]");
  });

  it("never removes the Next to me page", () => {
    cy.openConfigDialog(CONFIG_WITH_ON_THE_RUN);
    cy.openConfigurator();

    cy.nextToMeRow().should("contain", "in this config");
    cy.nextToMeRow().should("not.contain", "Remove");

    cy.closeConfigurator();
    cy.tomlEditor().should("contain.value", "[[on_the_run]]");
  });
});
