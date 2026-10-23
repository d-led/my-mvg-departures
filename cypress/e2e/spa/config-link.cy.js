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

const RAW_LINK =
  "https://raw.githubusercontent.com/d-led/my-mvg-departures/main/spa/configs/berlin-alexanderplatz.toml";
const GITHUB_PAGE =
  "https://github.com/d-led/my-mvg-departures/blob/main/spa/configs/berlin-alexanderplatz.toml";

function stubApis() {
  cy.intercept("**/api/bgw-pt/v3/**", { statusCode: 200, body: [] });
}

describe("SPA config links", () => {
  it("loads a config from a raw GitHub link", () => {
    stubApis();
    cy.intercept(RAW_LINK, { statusCode: 200, body: CONFIG_TOML }).as("config");

    cy.visit(`/?config=${encodeURIComponent(RAW_LINK)}`);

    cy.wait("@config");
    cy.get(".config-button").click();
    cy.get(".config-textarea").should("contain.value", 'title = "Linked config"');
    cy.get(".config-textarea").should("contain.value", "Giesing");
  });

  it("reads a GitHub file page through its raw host", () => {
    stubApis();
    cy.intercept(RAW_LINK, { statusCode: 200, body: CONFIG_TOML }).as("config");

    cy.visit(`/?config=${encodeURIComponent(GITHUB_PAGE)}`);

    cy.wait("@config");
    cy.get(".config-button").click();
    cy.get(".config-textarea").should("contain.value", 'title = "Linked config"');
  });

  it("fills the editor from the shipped Berlin example", () => {
    stubApis();
    cy.visit("/");

    cy.get(".config-button").click();
    cy.get(".info-links").contains("button", "Berlin Alexanderplatz").click();

    cy.get(".config-textarea").should("contain.value", "900100003");
    cy.get(".config-textarea").should("contain.value", 'api_provider = "vbb"');
  });
});
