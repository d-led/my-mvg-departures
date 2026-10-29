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

describe("SPA config links", () => {
  it("loads a config from a raw GitHub link", () => {
    stubApis();
    cy.intercept(RAW_LINK, { statusCode: 200, body: CONFIG_TOML }).as("config");

    cy.visit(`/?config=${encodeURIComponent(RAW_LINK)}`);

    cy.wait("@config");
    cy.openConfigButton();
    cy.openTomlView();
    cy.tomlEditor().should("contain.value", 'title = "Linked config"');
    cy.tomlEditor().should("contain.value", "Giesing");
  });

  it("reads a GitHub file page through its raw host", () => {
    stubApis();
    cy.intercept(RAW_LINK, { statusCode: 200, body: CONFIG_TOML }).as("config");

    cy.visit(`/?config=${encodeURIComponent(GITHUB_PAGE)}`);

    cy.wait("@config");
    cy.openConfigButton();
    cy.openTomlView();
    cy.tomlEditor().should("contain.value", 'title = "Linked config"');
  });

  it("offers the shipped example as one button, not a list", () => {
    stubApis();
    cy.visit("/");

    cy.openConfigButton();

    // One way to load it, and it is the example the app ships.
    cy.footerButton("Example").click();
    cy.tomlEditor().should("contain.value", 'title = "Giesing Departures"');
    cy.dialogContent().should("not.contain", "muenchen-muenchner-freiheit");
  });
});
