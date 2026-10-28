/**
 * The pages of a config are what the user rearranges, so the dialog shows them
 * as a list: drag a card, or tap the arrows, and save when the order is right.
 */
const CONFIG_TOML_KEY = "mvg_departures_config_toml";

const TWO_PAGES = `
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

function openConfigDialog() {
  cy.intercept("**/api/bgw-pt/v3/**", { statusCode: 200, body: [] });
  cy.visit("/", {
    onBeforeLoad(win) {
      win.localStorage.setItem(CONFIG_TOML_KEY, TWO_PAGES);
    },
  });
  cy.get(".config-button").click();
  cy.get(".config-textarea").should("be.visible");
  cy.get(".config-method-selector").contains("button", "Configurator").click();
  cy.get(".page-card, .pages-empty").should("exist");
}

function pageTitles() {
  return cy.get(".page-card .page-title strong");
}

/** One departure in the shape the MVG API returns. */
function departure(label, destination, transportType) {
  const time = Date.now() + 5 * 60 * 1000;
  return {
    realtimeDepartureTime: time,
    plannedDepartureTime: time,
    delayInMinutes: 0,
    platform: 1,
    realtime: true,
    label,
    destination,
    transportType,
    cancelled: false,
    messages: [],
  };
}

describe("SPA config pages", () => {
  it("shows every page with its stops", () => {
    openConfigDialog();

    pageTitles().should("have.length", 2);
    cy.get(".page-card").first().should("contain", "Giesing");
    cy.get(".page-card").eq(1).should("contain", "Hauptbahnhof");
  });

  it("moves a page up and keeps the new order on save", () => {
    openConfigDialog();

    cy.get('[aria-label="Move Work up"]').click();

    pageTitles().then(($titles) => {
      expect([...$titles].map((title) => title.textContent)).to.deep.equal(["Work", "Home"]);
    });

    cy.contains("button", "Save").click();

    cy.window()
      .its("localStorage")
      .invoke("getItem", CONFIG_TOML_KEY)
      .should((saved) => {
        const paths = saved
          .split("[[routes]]")
          .slice(1)
          .map((block) => /path\s*=\s*"([^"]*)"/.exec(block)?.[1]);

        expect(paths).to.deep.equal(["/work", "/"]);
        expect(saved).to.contain("Hauptbahnhof");
      });
  });

  it("opens on the TOML editor and keeps the Configurator as the last tab", () => {
    cy.intercept("**/api/bgw-pt/v3/**", { statusCode: 200, body: [] });
    cy.visit("/", {
      onBeforeLoad(win) {
        win.localStorage.setItem(CONFIG_TOML_KEY, TWO_PAGES);
      },
    });
    cy.get(".config-button").click();

    // The previous view is what opens: the editor, with the file in it.
    cy.get(".config-textarea").should("be.visible").and("contain.value", "[[routes]]");
    cy.get(".editor-highlight .hljs-section").should("exist");

    cy.get(".config-method-selector .method-button").then(($tabs) => {
      const labels = [...$tabs].map((tab) => tab.textContent.trim());

      expect(labels[labels.length - 1]).to.equal("Configurator");
      expect(labels.slice(0, -1)).to.deep.equal([
        "TOML Config",
        "Wizard (experimental)",
        "Delete (current route)",
        "Routes",
        "Clean up",
      ]);
    });

    cy.get(".page-card").should("not.exist");
    cy.get(".config-method-selector").contains("button", "Configurator").click();
    cy.get(".page-card").should("have.length", 2);
  });

  it("renames a page and says what a stop shows when nothing matches", () => {
    openConfigDialog();

    cy.get(".page-card").first().contains("button", "Edit").click();

    cy.get(".page-form input").first().clear().type("Zuhause");
    cy.get('.page-form input[aria-label="Heading for Giesing"]').type("Andere");
    cy.get('.page-form input[aria-label="Show unmatched departures of Giesing"]').check();
    cy.contains("button", "Apply changes").click();

    cy.get(".page-form").should("not.exist");
    pageTitles().first().should("have.text", "Zuhause");
    cy.get(".page-card").first().should("contain", "Andere");

    cy.contains("button", "Save").click();

    cy.window().its("localStorage").invoke("getItem", CONFIG_TOML_KEY).should((saved) => {
      expect(saved).to.contain('title = "Zuhause"');
      expect(saved).to.contain('ungrouped_title = "Andere"');
      expect(saved).to.contain("show_ungrouped = true");
    });
  });

  it("refuses a path another page already uses", () => {
    openConfigDialog();

    cy.get(".page-card").first().contains("button", "Edit").click();
    cy.contains("label", "Path").find("input").clear().type("/work");

    cy.get(".page-form-problem").should("contain", "already uses this path");
    cy.contains("button", "Apply changes").should("be.disabled");

    cy.get(".page-form").contains("button", "Cancel").click();
    cy.get(".page-form").should("not.exist");
    pageTitles().first().should("have.text", "Home");
  });

  it("shows a stop's headings and rewrites them", () => {
    openConfigDialog();

    cy.get(".page-card").first().should("contain", "1 heading");
    cy.get(".page-card").first().contains("button", "Edit").click();

    cy.get('.page-form-direction-name').should("have.value", "->City");
    cy.get('.page-form-direction textarea')
      .should("have.value", "U2 Messestadt\n19 Pasing")
      .clear()
      .type("U2 Messestadt\nU1 Sendlinger Tor");

    cy.contains("button", "Apply changes").click();
    cy.contains("button", "Save").click();

    cy.window().its("localStorage").invoke("getItem", CONFIG_TOML_KEY).should((saved) => {
      expect(saved).to.contain('[routes.stops.direction_mappings]');
      expect(saved).to.contain('"->City" = ["U2 Messestadt", "U1 Sendlinger Tor"]');
      expect(saved).not.to.contain("19 Pasing");
    });
  });

  it("adds a heading to a stop", () => {
    openConfigDialog();

    cy.get(".page-card").eq(1).contains("button", "Edit").click();
    cy.get(".page-card").eq(1).contains("button", "Add heading").click();

    cy.get('.page-form-direction-name').last().type("->Norden");
    cy.get(".page-form-direction textarea").last().type("U3 Moosach");
    cy.contains("button", "Apply changes").click();
    cy.contains("button", "Save").click();

    cy.window().its("localStorage").invoke("getItem", CONFIG_TOML_KEY).should((saved) => {
      expect(saved).to.contain('"->Norden" = ["U3 Moosach"]');
    });
  });
  it("edits the defaults every page inherits", () => {
    openConfigDialog();

    cy.get(".defaults-card").should("contain", "Nothing set here");
    cy.get(".defaults-card").contains("button", "Edit defaults").click();

    cy.get('.defaults-card input[aria-label="Refresh every (seconds)"]')
      .clear()
      .type("30");
    cy.get('.defaults-card select[aria-label="Theme"]').select("dark");
    cy.contains("button", "Apply defaults").click();

    cy.get(".defaults-card").should("contain", "2 settings set here");
    cy.contains("button", "Save").click();

    cy.window().its("localStorage").invoke("getItem", CONFIG_TOML_KEY).should((saved) => {
      expect(saved).to.contain("[display]");
      expect(saved).to.contain("refresh_interval_seconds = 30");
      expect(saved).to.contain('theme = "dark"');
    });
  });

  it("gives one page settings of its own", () => {
    openConfigDialog();

    cy.get(".page-card").first().contains("button", "Edit").click();
    cy.get('.page-form input[aria-label="Refresh every (seconds)"]').clear().type("5");
    cy.contains("button", "Apply changes").click();
    cy.contains("button", "Save").click();

    cy.window().its("localStorage").invoke("getItem", CONFIG_TOML_KEY).should((saved) => {
      const pageTable = saved.slice(saved.indexOf("[routes.display]"));

      expect(pageTable).to.contain("refresh_interval_seconds = 5");
      expect(saved).to.contain('title = "Work"');
    });
  });

  it("empties a setting by clearing the field", () => {
    openConfigDialog();

    cy.get(".page-card").first().contains("button", "Edit").click();
    cy.get('.page-form input[aria-label="Refresh every (seconds)"]').clear().type("5");
    cy.contains("button", "Apply changes").click();
    cy.get(".page-card").first().contains("button", "Edit").click();
    cy.get('.page-form input[aria-label="Refresh every (seconds)"]').clear();
    cy.contains("button", "Apply changes").click();
    cy.contains("button", "Save").click();

    cy.window().its("localStorage").invoke("getItem", CONFIG_TOML_KEY).should((saved) => {
      expect(saved).not.to.contain("refresh_interval_seconds");
      expect(saved).to.contain('title = "Home"');
    });
  });

  it("keeps the app usable when the page you are on is deleted", () => {
    cy.intercept("**/api/bgw-pt/v3/**", { statusCode: 200, body: [] });
    cy.visit("/#/work", {
      onBeforeLoad(win) {
        win.localStorage.setItem(CONFIG_TOML_KEY, TWO_PAGES);
      },
    });

    cy.get(".config-button").click();
    cy.get(".config-method-selector").contains("button", "Configurator").click();
    cy.get(".page-card").eq(1).contains("button", "Delete page").click();
    cy.get(".page-card").eq(1).contains("button", "Yes, delete").click();
    cy.contains("button", "Save").click();

    // The route in the address bar is gone: the app falls back to the first page
    // and takes the address bar with it.
    cy.get(".modal-content").should("not.exist");
    cy.get("h1").should("contain", "Home");
    cy.location("hash").should("not.contain", "/work");
    cy.get("body").should("not.contain", "undefined");
  });

  it("creates a new page and refuses a path that is taken", () => {
    openConfigDialog();

    cy.get(".pages-actions").contains("button", "New page").click();
    cy.get('.new-page-form input[aria-label="New page path"]').type("/work");
    cy.get(".new-page-form .page-form-problem").should("contain", "already uses this path");
    cy.contains("button", "Create page").should("be.disabled");

    cy.get('.new-page-form input[aria-label="New page path"]').clear().type("/office");
    cy.get('.new-page-form input[aria-label="New page title"]').type("Büro");
    cy.contains("button", "Create page").click();

    cy.get(".page-card").should("have.length", 3);
    pageTitles().eq(2).should("have.text", "Büro");

    cy.contains("button", "Save").click();

    cy.window().its("localStorage").invoke("getItem", CONFIG_TOML_KEY).should((saved) => {
      expect(saved).to.contain('path = "/office"');
      expect(saved).to.contain('title = "Büro"');
      expect(saved.indexOf('path = "/office"')).to.be.greaterThan(
        saved.indexOf('path = "/work"'),
      );
    });
  });

  it("restores the Next to me page and edits what it looks for", () => {
    openConfigDialog();

    cy.get(".page-row").should("contain", "is missing from this config");
    cy.get(".page-row").contains("button", "Restore").click();
    cy.get(".page-row").contains("button", "Edit").click();

    cy.get('.on-the-run-field input[aria-label="Radius (metres)"]')
      .clear()
      .type("250");
    cy.get('.on-the-run-field input[aria-label="APIs"]').clear().type("mvg, vbb");
    cy.get(".page-row-form").contains("button", "Apply").click();

    cy.get(".page-row-form").should("not.exist");
    cy.contains("button", "Save").click();

    cy.window().its("localStorage").invoke("getItem", CONFIG_TOML_KEY).should((saved) => {
      expect(saved).to.contain("radius_meters = 250");
      expect(saved).to.contain('use_adapters = ["mvg", "vbb"]');
      expect(saved).to.contain("max_departures_per_stop = 8");
    });
  });

  it("makes the departures page follow the headings it was given", () => {    openConfigDialog();

    // Registered after `openConfigDialog`, so it wins over that catch-all stub.
    cy.intercept("**/api/bgw-pt/v3/departures*", {
      statusCode: 200,
      body: [
        departure("U2", "Messestadt", "UBAHN"),
        departure("U6", "Garching-Forschungszentrum", "UBAHN"),
      ],
    });

    cy.get(".page-card").first().contains("button", "Edit").click();
    cy.get(".page-form-direction textarea").first().clear().type("U6 Garching");
    cy.contains("button", "Apply changes").click();
    cy.contains("button", "Save").click();

    cy.get('[aria-label="Departures for ->City"]', { timeout: 15000 }).should(
      "contain",
      "Garching",
    );
    cy.get('[aria-label="Departures for ->City"]').should(
      "not.contain",
      "Messestadt",
    );
  });});
