/**
 * The SPA's configuration dialog can rewrite a config written for the server
 * into the shape the browser app reads. The rewrite stays in the editor until
 * the user saves, so a legacy config keeps working until then.
 */
const CONFIG_TOML_KEY = "mvg_departures_config_toml";

const LEGACY_CONFIG = `
[display]
title = "SPA e2e"
banner_color = "#087BC4"

[api]
sleep_ms_between_calls = 500

[inky]
font_family = "hk_grotesk"

[[stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
show_ungrouped = true
`;

function openConfigDialog(configToml) {
  cy.intercept("**/api/bgw-pt/v3/**", { statusCode: 200, body: [] });
  cy.visit("/", {
    onBeforeLoad(win) {
      win.localStorage.setItem(CONFIG_TOML_KEY, configToml);
    },
  });
  cy.get(".config-button").click();
  cy.get(".view-tabs").contains("button", "TOML").click();
  cy.get(".config-textarea").should("be.visible");
}

describe("SPA config clean-up", () => {
  it("rewrites a server config into the SPA's shape and saves it on request", () => {
    openConfigDialog(LEGACY_CONFIG);

    cy.get(".config-textarea").should("contain.value", "[api]");

    cy.contains("button", "Clean up").click();

    // The rewrite is prepared, not applied: the editor still shows the old file.
    cy.get(".cleanup-review").should("contain", 'moved 1 stop into the route at "/"');
    cy.get(".config-textarea").should("contain.value", "[api]");

    cy.contains("button", "Apply clean-up").click();

    cy.get(".config-textarea").should("not.contain.value", "[api]");
    cy.get(".config-textarea").should("not.contain.value", "[inky]");
    cy.get(".config-textarea").should("contain.value", "[[routes]]");
    cy.get(".config-textarea").should("contain.value", "[[routes.stops]]");
    cy.get(".config-notice").should("contain", "removed [api], [inky]");
    cy.get(".config-notice").should("contain", 'moved 1 stop into the route at "/"');

    // The clean-up is only an edit: the stored config keeps working until saved.
    cy.window().its("localStorage").invoke("getItem", CONFIG_TOML_KEY).should("equal", LEGACY_CONFIG);

    cy.contains("button", "Save").click();

    cy.window()
      .its("localStorage")
      .invoke("getItem", CONFIG_TOML_KEY)
      .should((saved) => {
        expect(saved).to.contain("[[routes]]");
        expect(saved).to.contain('path = "/"');
        expect(saved).to.contain("de:09162:1110");
        expect(saved).not.to.contain("[api]");
        expect(saved).not.to.contain("banner_color");
      });
  });

  it("leaves the config alone when the clean-up is cancelled", () => {
    openConfigDialog(LEGACY_CONFIG);

    cy.contains("button", "Clean up").click();
    cy.contains("button", "Cancel clean-up").click();

    cy.get(".cleanup-review").should("not.exist");
    cy.get(".config-textarea").should("contain.value", "[api]");
    cy.get(".config-textarea").should("not.contain.value", "[[routes]]");
  });

  it("says so when there is nothing to clean up", () => {
    openConfigDialog(`
[display]
title = "SPA e2e"

[[routes]]
path = "/"

[[routes.stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
`);

    cy.contains("button", "Clean up").click();

    cy.get(".config-notice").should("contain", "already uses the SPA format");
  });
});
