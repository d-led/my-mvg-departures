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
}

function pageTitles() {
  return cy.get(".page-card .page-title strong");
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

  it("has a raw TOML view beside the pages", () => {
    openConfigDialog();

    cy.get(".view-tabs").contains("button", "TOML").click();
    cy.get(".config-textarea").should("contain.value", "[[routes]]");

    cy.get(".view-tabs").contains("button", "Pages").click();
    cy.get(".page-card").should("have.length", 2);
  });
});
