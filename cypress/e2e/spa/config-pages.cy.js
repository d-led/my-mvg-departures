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
});
