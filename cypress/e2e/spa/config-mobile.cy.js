/**
 * The configuration dialogs are the product: they have to work with a thumb on
 * a phone, not just on a laptop. These specs drive every dialog at phone sizes -
 * the routes, editing the raw TOML, the wizard, its clean-up, the Next to me
 * page and the full-screen editor - and fail when a dialog is wider than the
 * screen, does not fit into its height, or hides its controls behind an edge.
 *
 * The dialog's selectors and actions live in `cypress/support/commands.js`.
 */
const CONFIG_TOML = `
[display]
title = "Mobile e2e"
refresh_interval_seconds = 20

[[routes]]
path = "/"

[[routes.display]]
title = "Home"

[[routes.stops]]
station_id = "de:09162:1110"
station_name = "Giesing"

[routes.stops.direction_mappings]
"->City" = ["U2 Messestadt"]

[[routes]]
path = "/work"

[[routes.display]]
title = "Work"

[[routes.stops]]
station_id = "de:09162:1056"
station_name = "Balanstr."
`;

const ONE_ROUTE_TOML = `
[display]
title = "Eine Seite"

[[routes]]
path = "/"

[[routes.stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
`;

const LEGACY_TOML = `[display]
title = "Mobile e2e"

[api]
sleep_ms_between_calls = 500

[[stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
`;

const IPHONE = [390, 844];

describe("configuration dialogs on a phone", () => {
  beforeEach(() => {
    cy.viewport(...IPHONE);
  });

  it("opens on the TOML editor and saves from there", () => {
    cy.openConfigDialog(CONFIG_TOML);

    cy.expectNoSidewaysScroll();
    cy.expectInsideViewport(".modal-content");
    cy.expectTomlEditorUsable();
    cy.tomlEditor().should("contain.value", "Giesing");

    cy.openConfigurator();
    cy.configRouteNames().should("deep.equal", ["Home", "Work"]);
    cy.expectInsideViewport(".cfg .page-row");
    cy.expectTapTarget(".cfg .row-open");

    // Done goes back to the file, which the dialog opened on.
    cy.closeConfigurator();
    cy.expectTomlEditorUsable();

    cy.saveConfig();
    cy.storedConfig().should("contain", "Mobile e2e");
  });

  it("expands the editor to the whole screen and comes back", () => {
    cy.openConfigDialog(CONFIG_TOML);
    cy.openTomlView();

    cy.expandTomlEditor();
    cy.expectInsideViewport(".fullscreen-editor-content");

    cy.fullscreenEditor().type("# typed on a phone");
    cy.closeFullscreenEditor();

    cy.tomlEditor().should("contain.value", "# typed on a phone");
  });

  it("tweaks a value with the filter", () => {
    cy.openConfigDialog(CONFIG_TOML);
    cy.openTomlView();

    cy.openTweaks();
    cy.filterTweaks("title");
    cy.tweakSections().should("have.length.at.least", 1);
    cy.expectNoSidewaysScroll();

    cy.closeTweaks();
  });

  it("cleans up a config written for the server", () => {
    cy.openConfigDialog(LEGACY_TOML);

    cy.cleanUpConfig();
    cy.applyCleanUp();

    cy.configNotice().should("contain", "removed [api]");
    cy.tomlEditor().should("not.contain.value", "[api]");
    cy.expectNoSidewaysScroll();
  });

  it("puts the Next to me page back", () => {
    cy.openConfigDialog(CONFIG_TOML);
    cy.openConfigurator();

    cy.nextToMeRow().should("contain", "missing");
    cy.restoreNextToMePage();

    cy.nextToMeRow().should("contain", "in this config");
    cy.nextToMeRow().should("not.contain", "Restore");
  });

  it("deletes a stop from a route", () => {
    cy.openConfigDialog(CONFIG_TOML);
    cy.openConfigurator();

    cy.openConfigRoute("Home");
    cy.openConfigStop("Giesing");
    cy.deleteConfigStop("Giesing");
    cy.confirmConfigStopDeletion("Giesing");

    cy.configStopNames().should("not.contain", "Giesing");
    cy.expectNoSidewaysScroll();
  });

  it("deletes a route only after confirming it", () => {
    cy.openConfigDialog(CONFIG_TOML);
    cy.openConfigurator();

    cy.configRouteNames().should("deep.equal", ["Home", "Work"]);

    cy.openConfigRoute("Work");
    cy.deleteConfigRoute("Work");
    cy.cancelConfigRouteDeletion();
    cy.configRouteNames().should("deep.equal", ["Home", "Work"]);

    // Declining leaves the route open, so it can be deleted from where it is.
    cy.deleteConfigRoute("Work");
    cy.confirmConfigRouteDeletion("Work");
    cy.configRouteNames().should("deep.equal", ["Home"]);
  });

  it("gives every row a control a thumb can hit", () => {
    cy.openConfigDialog(CONFIG_TOML);
    cy.openConfigurator();
    cy.openConfigRoute("Home");

    cy.expectTapTarget(".cfg .row-open", 44);
    cy.expectTapTarget(".cfg .grip", 44);
    cy.expectTapTarget(".cfg .button", 44);
  });

  it("edits the common settings in sections, not one long column", () => {
    cy.openConfigDialog(CONFIG_TOML);
    cy.openConfigurator();

    cy.openConfigDefaults();
    cy.expectNoSidewaysScroll();

    cy.configFieldSections().should("have.length", 3);
    cy.configInput("Line").should("have.attr", "placeholder", "4rem");
    cy.configButton("Apply").click();

    // A form nobody edited leaves the file exactly as it was.
    cy.closeConfigurator();
    cy.tomlEditor().should("have.value", CONFIG_TOML);
  });

  it("renames a route in a form that fits the screen", () => {
    cy.openConfigDialog(CONFIG_TOML);
    cy.openConfigurator();

    cy.openConfigRoute("Home");
    cy.openConfigRouteSettings();
    cy.retypeConfigInput("Route title", "Zuhause");
    cy.expectNoSidewaysScroll();
    cy.configButton("Apply").click();

    cy.configRouteNames().should("deep.equal", ["Zuhause", "Work"]);
  });

  it("edits what Next to me looks for on a phone", () => {
    cy.openConfigDialog(CONFIG_TOML);
    cy.openConfigurator();

    cy.restoreNextToMePage();
    cy.editNextToMePage();
    cy.nextToMeField("Radius (metres)").clear().type("250");
    cy.expectNoSidewaysScroll();
    cy.applyNextToMeForm();

    cy.nextToMeForm().should("not.exist");
  });

  it("creates a route on a phone", () => {
    cy.openConfigDialog(CONFIG_TOML);
    cy.openConfigurator();

    cy.addConfigRoute();
    cy.retypeConfigInput("New route path", "/home");
    cy.configInput("New route title").type("Zuhause");
    cy.expectNoSidewaysScroll();
    cy.configButton("Create").click();

    cy.configRouteNames().should("deep.equal", ["Home", "Work", "Zuhause"]);
  });

  it("edits the defaults on a phone", () => {
    cy.openConfigDialog(CONFIG_TOML);
    cy.openConfigurator();

    cy.openConfigDefaults();
    cy.configSelect("Theme").select("dark");
    cy.expectNoSidewaysScroll();
    cy.configButton("Apply").click();

    cy.saveConfigDialog();
    cy.storedConfig().should("contain", 'theme = "dark"');
  });

  it("adds a direction to a stop without leaving the screen", () => {
    cy.openConfigDialog(CONFIG_TOML);
    cy.openConfigurator();

    cy.openConfigRoute("Home");
    cy.openConfigStop("Giesing");
    cy.addConfigDirection();
    cy.retypeConfigInput("Name of direction 2 of Giesing", "->Norden");
    cy.expectNoSidewaysScroll();
    cy.configInput("Add a match to direction 2 of Giesing").type("U2 Messestadt{enter}");

    cy.saveConfigDialog();
    cy.storedConfig().should("contain", '"->Norden"');
  });

  it("deletes a header of the current route", () => {
    cy.openConfigDialog(CONFIG_TOML);

    cy.openHeaderDeletion();
    cy.headerDeletionItems().first().click();
    cy.reviewDeletion();
    cy.confirmDeletion();

    cy.headerDeletionItems().should("not.exist");
    cy.openTomlView();
    cy.tomlEditor().should("not.contain.value", "->City");
  });

  it("lists every route and deletes the one that is ticked", () => {
    cy.openConfigDialog(CONFIG_TOML);

    cy.openRouteDeletion();
    cy.routeDeletionItems().should("have.length", 2);

    cy.routeDeletionItems().contains("/work").click();
    cy.reviewDeletion();
    cy.confirmDeletion();

    cy.routeDeletionItems().should("not.exist");
    cy.tomlEditor().should("not.contain.value", 'path = "/work"');
  });

  it("refuses to delete the last route of a config", () => {
    cy.openConfigDialog(ONE_ROUTE_TOML);

    cy.openRouteDeletion();
    cy.routeDeletionItems().should("have.length", 1);
    cy.routeDeletionItems().first().click();

    cy.reviewDeletionButton().should("be.disabled");
    cy.routeDeletionHint().should("contain", "A configuration needs a page");
  });

  it("opens the wizard from the mode row on a small phone", () => {
    cy.viewport(320, 568);
    cy.openConfigDialog(CONFIG_TOML);

    cy.openWizard();

    cy.expectNoSidewaysScroll();
  });

  it("adds a stop with the wizard", () => {
    cy.openConfigDialog(CONFIG_TOML);
    cy.openConfigurator();

    // Registered after the visit, so it wins over the catch-all stub.
    cy.intercept("**/api/bgw-pt/v3/locations*", {
      statusCode: 200,
      body: [
        {
          globalId: "de:09162:2000",
          name: "Marienplatz",
          place: "München",
          type: "STATION",
        },
      ],
    });

    cy.openStopWizard();
    cy.expectNoSidewaysScroll();
    cy.expectInsideViewport(".wizard-content");

    cy.wizardPickMain();
    cy.wizardSearchStop("Marienplatz");
    cy.wizardPickFirstStop();
    cy.wizardNext();
    cy.wizardCreate();

    cy.saveConfigDialog();
    cy.storedConfig().should("contain", "Marienplatz");
  });
});

describe("configuration dialogs on small phones", () => {
  const SMALL_PHONES = [
    [320, 568],
    [360, 640],
    [375, 667],
  ];

  SMALL_PHONES.forEach(([width, height]) => {
    it(`fits the whole dialog into ${width}x${height}`, () => {
      cy.viewport(width, height);
      cy.openConfigDialog(CONFIG_TOML);

      cy.expectNoSidewaysScroll();
      cy.expectInsideViewport(".modal-content");
      cy.expectTomlEditorUsable();

      cy.openConfigurator();
      cy.configRouteNames().should("deep.equal", ["Home", "Work"]);
      cy.expectInsideViewport(".cfg .page-row");

      // The way out has to be reachable with one thumb: tapping Save proves it.
      cy.saveConfigDialog();
    });
  });
});
