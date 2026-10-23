/**
 * The "Next to me" page is one optional TOML table. It is easy to lose by
 * accident (an editor that rewrote the file), so the dialog can put it back -
 * and never takes it away.
 */
const CONFIG_TOML_KEY = "mvg_departures_config_toml";

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

function openConfigDialog(configToml) {
  cy.intercept("**/api/bgw-pt/v3/**", { statusCode: 200, body: [] });
  cy.visit("/", {
    onBeforeLoad(win) {
      win.localStorage.setItem(CONFIG_TOML_KEY, configToml);
    },
  });
  cy.get(".config-button").click();
}

function openTomlView() {
  cy.get(".view-tabs").contains("button", "TOML").click();
  cy.get(".config-textarea").should("be.visible");
}

describe("SPA config editing", () => {
  it("puts the Next to me page back into a config that lost it", () => {
    openConfigDialog(CONFIG_WITHOUT_ON_THE_RUN);

    cy.get(".page-row").should("contain", "is missing from this config");
    cy.get(".page-row").contains("button", "Restore").click();

    openTomlView();
    cy.get(".config-textarea").should("contain.value", "[[on_the_run]]");
    cy.get(".config-notice").should("contain", "Next to me is back");

    cy.contains("button", "Save").click();

    cy.window()
      .its("localStorage")
      .invoke("getItem", CONFIG_TOML_KEY)
      .should((saved) => {
        expect(saved).to.contain("[[on_the_run]]");
        expect(saved).to.contain("radius_meters = 50");
        expect(saved).to.contain("de:09162:1110");
      });
  });

  it("never removes the Next to me page", () => {
    openConfigDialog(CONFIG_WITH_ON_THE_RUN);

    cy.get(".page-row").should("contain", "is part of this config");
    cy.get(".page-row").should("not.contain", "Remove");

    openTomlView();
    cy.get(".config-textarea").should("contain.value", "[[on_the_run]]");
  });
});
