/**
 * The SPA's configuration dialog can rewrite a config written for the server
 * into the shape the browser app reads. The rewrite is a command - looking at a
 * screen never touches the file - and it edits the text instead of reprinting
 * it, so comments and the author's layout survive.
 */
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

/** The author's comments and spacing, and the server's tables next to them. */
const HAND_WRITTEN_CONFIG = `# Giesing, as the server had it.
[display]
title   = "SPA e2e"     # lined up by hand
banner_color = "#087BC4"

# Read by the server only
[api]
sleep_ms_between_calls = 500

# The stop itself
[[stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
`;

describe("SPA config clean-up", () => {
  it("rewrites a server config into the SPA's shape and saves it on request", () => {
    cy.openConfigDialog(LEGACY_CONFIG);
    cy.tomlEditor().should("contain.value", "[api]");

    cy.cleanUpConfig();

    // The rewrite is prepared, not applied: the editor still shows the old file.
    cy.cleanUpReview().should("contain", 'moved 1 stop into the route at "/"');
    cy.tomlEditor().should("contain.value", "[api]");

    cy.applyCleanUp();

    cy.tomlEditor().should("not.contain.value", "[api]");
    cy.tomlEditor().should("not.contain.value", "[inky]");
    cy.tomlEditor().should("contain.value", "[[routes]]");
    cy.tomlEditor().should("contain.value", "[[routes.stops]]");
    cy.configNotice().should("contain", "removed [api], [inky]");
    cy.configNotice().should("contain", 'moved 1 stop into the route at "/"');

    // The clean-up is only an edit: the stored config keeps working until saved.
    cy.storedConfig().should("equal", LEGACY_CONFIG);

    cy.saveConfig();

    cy.storedConfig().should((saved) => {
      expect(saved).to.contain("[[routes]]");
      expect(saved).to.contain('path = "/"');
      expect(saved).to.contain("de:09162:1110");
      expect(saved).not.to.contain("[api]");
      expect(saved).not.to.contain("banner_color");
    });
  });

  it("keeps the comments and the layout of everything it does not touch", () => {
    cy.openConfigDialog(HAND_WRITTEN_CONFIG);

    cy.cleanUpConfig();
    cy.applyCleanUp();

    cy.tomlEditor().should("contain.value", "# Giesing, as the server had it.");
    cy.tomlEditor().should("contain.value", 'title   = "SPA e2e"     # lined up by hand');
    cy.tomlEditor().should("contain.value", "# The stop itself");
    cy.tomlEditor().should("not.contain.value", "banner_color");
    cy.tomlEditor().should("not.contain.value", "# Read by the server only");
  });

  it("leaves the file alone when a screen is opened", () => {
    cy.openConfigDialog(LEGACY_CONFIG);

    cy.openConfigurator();
    cy.closeConfigurator();

    cy.tomlEditor().should("have.value", LEGACY_CONFIG);
  });

  it("leaves the config alone when the clean-up is cancelled", () => {
    cy.openConfigDialog(LEGACY_CONFIG);

    cy.cleanUpConfig();
    cy.cancelCleanUp();

    cy.cleanUpReview().should("not.exist");
    cy.tomlEditor().should("contain.value", "[api]");
    cy.tomlEditor().should("not.contain.value", "[[routes]]");
  });

  it("says so when there is nothing to clean up", () => {
    cy.openConfigDialog(`
[display]
title = "SPA e2e"

[[routes]]
path = "/"

[[routes.stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
`);

    cy.cleanUpConfig();

    cy.configNotice().should("contain", "already uses the SPA format");
  });
});
