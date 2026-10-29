/**
 * The configurator shows one context at a time: the routes, one route's stops,
 * or one stop's directions. Every edit lands in the TOML the dialog saves.
 *
 * The dialog's selectors and actions live in `cypress/support/commands.js`.
 */
const CONFIG_TOML_KEY = "mvg_departures_config_toml";

const TWO_ROUTES = `
[display]
title = "Pages e2e"

[[routes]]
path = "/"

[[routes.display]]
title = "Home"

[[routes.stops]]
station_id = "de:09162:1110"
station_name = "Giesing"

[routes.stops.direction_mappings]
"->City" = ["U2 Messestadt", "19 Pasing"]

[[routes]]
path = "/work"

[[routes.display]]
title = "Work"

[[routes.stops]]
station_id = "de:09162:1000"
station_name = "Hauptbahnhof"
`;

function visitWithConfig(hash = "/") {
  cy.intercept("**/api/bgw-pt/v3/**", { statusCode: 200, body: [] });
  cy.visit(hash, {
    onBeforeLoad(win) {
      win.localStorage.setItem(CONFIG_TOML_KEY, TWO_ROUTES);
    },
  });
}

describe("SPA configurator", () => {
  it("lists every route as one row, with what it holds", () => {
    visitWithConfig();
    cy.openConfigurator();

    cy.configRouteNames().should("deep.equal", ["Home", "Work"]);
    cy.configPanel().should("contain", "1 stop");
  });

  it("opens one route at a time", () => {
    visitWithConfig();
    cy.openConfigurator();

    cy.openConfigRoute("Home");
    cy.configStopNames().should("deep.equal", ["Giesing"]);

    cy.openConfigRoute("Work");
    cy.configStopNames().should("deep.equal", ["Hauptbahnhof"]);
  });

  it("opens one stop at a time, and shows its name for editing", () => {
    visitWithConfig();
    cy.openConfigurator();
    cy.openConfigRoute("Home");

    cy.openConfigStop("Giesing");
    cy.configInput("Name of Giesing").should("be.visible").and("have.value", "Giesing");
  });

  it("opens a route and a stop by tapping the name, not only the triangle", () => {
    visitWithConfig();
    cy.openConfigurator();

    cy.tapConfigRouteName("Home");
    cy.configStopNames().should("deep.equal", ["Giesing"]);

    cy.tapConfigStopName("Giesing");
    cy.configInput("Name of Giesing").should("be.visible");
  });

  it("moves a route down, and keeps the new order on save", () => {
    visitWithConfig();
    cy.openConfigurator();

    cy.moveConfigRouteWithKeyboard("Home", "down");
    cy.configRouteNames().should("deep.equal", ["Work", "Home"]);
    cy.saveConfigDialog();

    cy.storedConfig().should((saved) => {
      const paths = saved
        .split("[[routes]]")
        .slice(1)
        .map((block) => /path\s*=\s*"([^"]*)"/.exec(block)?.[1]);

      expect(paths).to.deep.equal(["/work", "/"]);
      expect(saved).to.contain("Hauptbahnhof");
    });
  });

  it("opens on the TOML editor and keeps the Configurator as the last tab", () => {
    visitWithConfig();

    cy.openConfigButton();
    cy.tomlEditor().should("contain.value", "[[routes]]");
    cy.configTabs().then(($tabs) => {
      const labels = [...$tabs].map((tab) => tab.textContent.trim());

      expect(labels[labels.length - 1]).to.equal("Configurator");
    });
    cy.configPanel().should("not.exist");
  });

  it("renames a route, a stop and what the unmatched departures show under", () => {
    visitWithConfig();
    cy.openConfigurator();

    cy.openConfigRoute("Home");
    cy.openConfigRouteSettings();
    cy.retypeConfigInput("Route title", "Zuhause");
    cy.configButton("Apply").click();
    cy.configRouteNames().should("deep.equal", ["Zuhause", "Work"]);

    cy.openConfigStop("Giesing");
    cy.retypeConfigInput("Name of Giesing", "Giesing Bf");
    cy.retypeConfigInput("Heading for Giesing Bf", "Andere");
    cy.configInput("Show unmatched departures of Giesing Bf").check();
    cy.saveConfigDialog();

    cy.storedConfig().should((saved) => {
      expect(saved).to.contain('title = "Zuhause"');
      expect(saved).to.contain('station_name = "Giesing Bf"');
      expect(saved).to.contain('ungrouped_title = "Andere"');
      expect(saved).to.contain("show_ungrouped = true");
    });
  });

  it("refuses a path another route already uses", () => {
    visitWithConfig();
    cy.openConfigurator();

    cy.openConfigRoute("Home");
    cy.openConfigRouteSettings();
    cy.retypeConfigInput("Route path", "/work");

    cy.configProblem().should("contain", "already uses this path");
    cy.configButton("Apply").should("be.disabled");

    cy.configButton("Cancel").click();
    cy.configRouteNames().should("deep.equal", ["Home", "Work"]);
  });

  it("keeps a direction's matches editable instead of toggling them away", () => {
    visitWithConfig();
    cy.openConfigurator();

    cy.openConfigRoute("Home");
    cy.openConfigStop("Giesing");
    cy.openConfigDirection();

    cy.configMatches().should("have.length", 2).first().should("have.value", "U2 Messestadt");
    cy.retypeConfigMatch(0, "U1 Sendlinger Tor");
    cy.removeConfigMatch(1);
    cy.configMatches().should("have.length", 1).and("have.value", "U1 Sendlinger Tor");
    cy.saveConfigDialog();

    cy.storedConfig().should((saved) => {
      expect(saved).to.contain('"->City" = ["U1 Sendlinger Tor"]');
      expect(saved).not.to.contain("19 Pasing");
    });
  });

  it("adds a match that the stop's departures never named", () => {
    visitWithConfig();
    cy.openConfigurator();

    cy.openConfigRoute("Home");
    cy.openConfigStop("Giesing");
    cy.openConfigDirection();
    cy.configInput("Add a match to direction 1 of Giesing").type("N44{enter}");

    cy.configMatches().last().should("have.value", "N44");
    cy.saveConfigDialog();

    cy.storedConfig().should((saved) => {
      expect(saved).to.contain('"->City" = ["U2 Messestadt", "19 Pasing", "N44"]');
    });
  });

  it("adds a direction to a stop", () => {
    visitWithConfig();
    cy.openConfigurator();

    cy.openConfigRoute("Work");
    cy.openConfigStop("Hauptbahnhof");
    cy.addConfigDirection();

    cy.retypeConfigInput("Name of direction 1 of Hauptbahnhof", "->Norden");
    cy.configInput("Add a match to direction 1 of Hauptbahnhof").type("U3 Moosach{enter}");
    cy.saveConfigDialog();

    cy.storedConfig().should((saved) => {
      expect(saved).to.contain('"->Norden" = ["U3 Moosach"]');
    });
  });

  it("edits the defaults every route inherits, font sizes included", () => {
    visitWithConfig();
    cy.openConfigurator();

    cy.openConfigDefaults();
    cy.retypeConfigInput("Refresh every (seconds)", "30");
    cy.configSelect("Theme").select("dark");
    cy.retypeConfigInput("Line", "3rem");
    cy.configButton("Apply").click();
    cy.saveConfigDialog();

    cy.storedConfig().should((saved) => {
      expect(saved).to.contain("[display]");
      expect(saved).to.contain("refresh_interval_seconds = 30");
      expect(saved).to.contain('theme = "dark"');
      expect(saved).to.contain('font_size_route_number = "3rem"');
    });
  });

  it("gives one route settings of its own", () => {
    visitWithConfig();
    cy.openConfigurator();

    cy.openConfigRoute("Home");
    cy.openConfigRouteSettings();
    cy.retypeConfigInput("Refresh every (seconds)", "5");
    cy.configButton("Apply").click();
    cy.saveConfigDialog();

    cy.storedConfig().should((saved) => {
      const routeTable = saved.slice(saved.indexOf("[routes.display]"));

      expect(routeTable).to.contain("refresh_interval_seconds = 5");
      expect(saved).to.contain('title = "Work"');
    });
  });

  it("keeps the app usable when the route you are on is deleted", () => {
    visitWithConfig("/#/work");
    cy.openConfigurator();

    cy.openConfigRoute("Work");
    cy.deleteConfigRoute("Work");
    cy.confirmConfigRouteDeletion("Work");
    cy.saveConfigDialog();

    cy.dialogClosed();
    cy.mainHeadline().should("contain", "Home");
    cy.location("hash").should("not.contain", "/work");
    cy.appBody().should("not.contain", "undefined");
  });

  it("creates a new route and refuses a path that is taken", () => {
    visitWithConfig();
    cy.openConfigurator();

    cy.addConfigRoute();
    cy.configInput("New route path").type("/work");
    cy.configProblem().should("contain", "already uses this path");
    cy.configButton("Create").should("be.disabled");

    cy.retypeConfigInput("New route path", "/office");
    cy.configInput("New route title").type("Büro");
    cy.configButton("Create").click();

    cy.configRouteNames().should("deep.equal", ["Home", "Work", "Büro"]);
    cy.saveConfigDialog();

    cy.storedConfig().should((saved) => {
      expect(saved).to.contain('path = "/office"');
      expect(saved).to.contain('title = "Büro"');
      expect(saved.indexOf('path = "/office"')).to.be.greaterThan(saved.indexOf('path = "/work"'));
    });
  });

  it("adds a stop by searching for its name", () => {
    cy.intercept("**/api/bgw-pt/v3/locations**", {
      statusCode: 200,
      body: [
        {
          type: "STATION",
          globalId: "de:09162:1110",
          name: "Giesing",
          place: "München",
          latitude: 48.110861,
          longitude: 11.595247,
        },
      ],
    });
    cy.intercept("**/api/bgw-pt/v3/departures**", { statusCode: 200, body: [] });
    cy.visit("/", {
      onBeforeLoad(win) {
        win.localStorage.setItem(CONFIG_TOML_KEY, TWO_ROUTES);
      },
    });
    cy.openConfigurator();

    cy.openConfigRoute("Work");
    cy.addConfigStop();
    cy.searchConfigStop("Giesing");
    cy.pickConfigStop("Giesing");

    cy.configStopNames().should("deep.equal", ["Hauptbahnhof", "Giesing"]);
    cy.saveConfigDialog();

    cy.storedConfig().should((saved) => {
      const work = saved.slice(saved.indexOf('path = "/work"'));

      expect(work).to.contain('station_id = "de:09162:1110"');
      expect(work).to.contain("Hauptbahnhof");
    });
  });

  it("deletes a stop of the route that is open", () => {
    visitWithConfig();
    cy.openConfigurator();

    cy.openConfigRoute("Home");
    cy.openConfigStop("Giesing");
    cy.deleteConfigStop("Giesing");
    cy.confirmConfigStopDeletion("Giesing");

    cy.configStopNames().should("deep.equal", []);
    cy.saveConfigDialog();

    cy.storedConfig().should((saved) => {
      expect(saved).not.to.contain("de:09162:1110");
      expect(saved).to.contain("Hauptbahnhof");
    });
  });
});
