/**
 * A config can be shared as a link: `?config=<url>`. Raw GitHub links are the
 * useful ones (they are served as plain text), and GitHub's file pages are
 * translated to the raw host for convenience. The samples that ship with the
 * app load the same way.
 */
const CONFIG_TOML = `
[display]
title = "Linked config"

[[routes]]
path = "/"

[[routes.stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
`.trim();

const RAW_LINK = "https://raw.githubusercontent.com/d-led/my-mvg-departures/main/spa/configs/berlin-alexanderplatz.toml";
const GITHUB_PAGE = "https://github.com/d-led/my-mvg-departures/blob/main/spa/configs/berlin-alexanderplatz.toml";

function stubApis() {
  cy.intercept("**/api/bgw-pt/v3/**", { statusCode: 200, body: [] });
}

function openTomlView() {
  cy.get(".config-method-selector").contains("button", "Manual TOML").click();
  cy.get(".config-textarea").should("be.visible");
}

describe("SPA config links", () => {
  it("loads a config from a raw GitHub link", () => {
    stubApis();
    cy.intercept(RAW_LINK, { statusCode: 200, body: CONFIG_TOML }).as("config");

    cy.visit(`/?config=${encodeURIComponent(RAW_LINK)}`);

    cy.wait("@config");
    cy.get(".config-button").click();
    openTomlView();
    cy.get(".config-textarea").should("contain.value", 'title = "Linked config"');
    cy.get(".config-textarea").should("contain.value", "Giesing");
  });

  it("reads a GitHub file page through its raw host", () => {
    stubApis();
    cy.intercept(RAW_LINK, { statusCode: 200, body: CONFIG_TOML }).as("config");

    cy.visit(`/?config=${encodeURIComponent(GITHUB_PAGE)}`);

    cy.wait("@config");
    cy.get(".config-button").click();
    openTomlView();
    cy.get(".config-textarea").should("contain.value", 'title = "Linked config"');
  });

  it("keeps the example list out of the dialog", () => {
    stubApis();
    cy.visit("/");

    cy.get(".config-button").click();

    // The only example left is the one button that loads the default config.
    cy.get(".modal-content").should("not.contain", "Münchner Freiheit");
    cy.get(".modal-footer").contains("button", "Example").should("be.visible");
  });
});
