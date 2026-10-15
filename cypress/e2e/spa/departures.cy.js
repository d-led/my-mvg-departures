/**
 * End-to-end coverage for the SPA served as static files.
 *
 * The MVG API is stubbed, so the tests are hermetic and can reproduce a partial
 * outage: one stop answers, the other one keeps returning 503.
 */
const STOP_WITH_DEPARTURES = "de:09162:1110";
const STOP_THAT_FAILS = "de:09162:1056";

const CONFIG_TOML_KEY = "mvg_departures_config_toml";
const CONFIG_TOML = `
[display]
title = "SPA e2e"
refresh_interval_seconds = 20

[[stops]]
station_id = "${STOP_WITH_DEPARTURES}"
station_name = "Giesing"
show_ungrouped = true

[[stops]]
station_id = "${STOP_THAT_FAILS}"
station_name = "Balanstr."
show_ungrouped = true
`;

function mvgDepartures() {
  const departureTime = Date.now() + 5 * 60 * 1000;
  return [
    {
      realtimeDepartureTime: departureTime,
      plannedDepartureTime: departureTime,
      delayInMinutes: 0,
      platform: 1,
      realtime: true,
      label: "U6",
      destination: "Garching-Forschungszentrum",
      transportType: "UBAHN",
      cancelled: false,
      messages: [],
    },
  ];
}

/** Station coordinate lookups are not under test: keep them off the network. */
function stubStationLookups() {
  cy.intercept("**/api/bgw-pt/v3/stations*", {
    statusCode: 200,
    body: [],
  }).as("stationLookups");
}

/**
 * Answers the departure requests: the failing stops keep returning 503.
 * Attempts per stop are counted so a test can show that retries happened.
 */
function stubDepartures({ failingStops = [], attemptCounts = {} } = {}) {
  cy.intercept(
    { method: "GET", url: "**/api/bgw-pt/v3/departures*" },
    (request) => {
      const globalId = new URL(request.url).searchParams.get("globalId");
      attemptCounts[globalId] = (attemptCounts[globalId] ?? 0) + 1;

      if (failingStops.includes(globalId)) {
        request.reply({ statusCode: 503, body: "Service Unavailable" });
        return;
      }
      request.reply({ statusCode: 200, body: mvgDepartures() });
    },
  );
}

function openSpa() {
  cy.visit("/", {
    onBeforeLoad(win) {
      win.localStorage.setItem(CONFIG_TOML_KEY, CONFIG_TOML);
    },
  });
}

describe("SPA departures", () => {
  it("shows the departures of the healthy stops when one stop is down", () => {
    stubStationLookups();
    stubDepartures({ failingStops: [STOP_THAT_FAILS] });
    openSpa();

    cy.get("#departures .departure-row", { timeout: 15000 }).should(
      "have.length.at.least",
      1,
    );
    cy.get("#departures").should("contain", "Garching-Forschungszentrum");
  });

  it("retries the failing stop inside the refresh cycle", () => {
    const attemptCounts = {};

    stubStationLookups();
    stubDepartures({
      failingStops: [STOP_THAT_FAILS],
      attemptCounts,
    });
    openSpa();

    // The marker only appears once the cycle is over, i.e. once the failing stop
    // has used up its attempts - all within the first cycle, without waiting for
    // the next refresh interval.
    cy.get("#departures", { timeout: 15000 }).should(
      "contain",
      "No data (refresh failed)",
    );

    cy.then(() => {
      expect(attemptCounts[STOP_THAT_FAILS]).to.equal(3);
      expect(attemptCounts[STOP_WITH_DEPARTURES]).to.equal(1);
    });
  });

  it("keeps the failure out of the way while departures are on screen", () => {
    stubStationLookups();
    stubDepartures({ failingStops: [STOP_THAT_FAILS] });
    openSpa();

    cy.get("#departures .departure-row", { timeout: 15000 }).should(
      "have.length.at.least",
      1,
    );

    // No banner on top of the departures ...
    cy.get(".stop-failures").should("not.exist");
    // ... but the failed stop says so where it belongs ...
    cy.get("#departures").should("contain", "No data (refresh failed)");
    // ... and the status indicator reports the degradation with a reason.
    cy.get("#api-status-container")
      .should("have.attr", "aria-label")
      .and("contain", "degraded");
    cy.get("#api-status-container")
      .invoke("attr", "title")
      .should("contain", "No data from Balanstr.");
  });

  it("announces the failures when there is nothing else to show", () => {
    stubStationLookups();
    stubDepartures({ failingStops: [STOP_WITH_DEPARTURES, STOP_THAT_FAILS] });
    openSpa();

    cy.get(".stop-failures", { timeout: 15000 })
      .should("be.visible")
      .and("contain", "No data from 2 stops");
    cy.get("#api-status-container")
      .should("have.attr", "aria-label")
      .and("contain", "API status: error");
  });
});
