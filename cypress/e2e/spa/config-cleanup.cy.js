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

/** A whole config written for the server: stops at the top level, no routes. */
const SERVER_FORMAT = `[display]
title = "St.-Ingbert Departures"
fill_vertical_space = true

[[stops]]
station_id = "de:09162:1044:1:1"
station_name = "Ungsteiner Str."
max_departures_per_stop = 4
max_departures_per_route = 3
max_hours_in_advance = 3
show_ungrouped = true
ungrouped_title = "Giesing"

[stops.direction_mappings]
"->Ostbahnhof" = ["54 Münchner Freiheit"]

[[stops]]
station_id = "de:09162:1107:2:2"
station_name = "Werinherstraße"
max_departures_per_stop = 4
show_ungrouped = true
ungrouped_title = "Stachus"
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

  it("shows a server config's stops instead of pretending there are none", () => {
    cy.openConfigDialog(SERVER_FORMAT);
    cy.openConfigurator();

    // The board reads the top level stops as the route at "/", and so does this.
    cy.configRouteNames().should("deep.equal", ["/"]);
    cy.configPanel().should("contain", "server format");
    cy.configPanel().should("contain", "Ungsteiner Str.");
    cy.configPanel().should("contain", "Werinherstraße");
    cy.configPanel().should("contain", "1 direction");

    cy.convertConfigToRoutes();

    // The conversion is a proposal, shown in the file it would rewrite.
    cy.cleanUpReview().should("contain", 'moved 2 stops into the route at "/"');
    cy.applyCleanUp();
    cy.tomlEditor().should("contain.value", "[[routes.stops]]");

    cy.openConfigurator();
    cy.configRouteNames().should("deep.equal", ["/"]);
    cy.configPanel().should("not.contain", "server format");
    cy.openConfigRoute("/");
    cy.configStopNames().should("deep.equal", [
      "Ungsteiner Str.",
      "Werinherstraße",
    ]);
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
