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

function openSpa(configToml = CONFIG_TOML) {
  cy.visit("/", {
    onBeforeLoad(win) {
      win.localStorage.setItem(CONFIG_TOML_KEY, configToml);
    },
  });
}

/** The rows one stop shows, wherever the other stops put theirs. */
function rowsOf(stopName) {
  return cy
    .contains(".direction-header", stopName)
    .parent()
    .find(".departure-row");
}

/**
 * Tabs away and back: the app then refreshes at once, which is the only way to
 * watch a second cycle without waiting out the refresh interval.
 */
function refreshAtOnce() {
  cy.document().then((document) => {
    const pretendHidden = (hidden) => {
      Object.defineProperty(document, "hidden", {
        configurable: true,
        value: hidden,
      });
      document.dispatchEvent(new Event("visibilitychange"));
    };
    pretendHidden(true);
    pretendHidden(false);
  });
}

/** The same config, but without the in-cycle retries. */
const CONFIG_TOML_SINGLE_ATTEMPT = CONFIG_TOML.replace(
  "refresh_interval_seconds = 20",
  "refresh_interval_seconds = 20\nfetch_retry_attempts = 1",
);

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

  it("shows a bus stand number where a rail departure shows its platform", () => {
    stubStationLookups();
    cy.intercept(
      { method: "GET", url: "**/api/bgw-pt/v3/departures*" },
      (request) => {
        const time = Date.now() + 5 * 60 * 1000;
        request.reply({
          statusCode: 200,
          body: [
            {
              realtimeDepartureTime: time,
              plannedDepartureTime: time,
              delayInMinutes: 0,
              stopPositionNumber: 10,
              realtime: true,
              label: "220",
              destination: "Winning, Riegerweg/Altersheim",
              transportType: "REGIONAL_BUS",
              cancelled: false,
              messages: [],
            },
          ],
        });
      },
    );
    openSpa();

    cy.get("#departures .platform", { timeout: 15000 })
      .first()
      .should("have.text", "10")
      .and("have.class", "stand");
  });

  it("says how far a slow refresh has got while the screen is empty", () => {
    stubStationLookups();
    cy.intercept(
      { method: "GET", url: "**/api/bgw-pt/v3/departures*" },
      (request) => {
        request.reply({ delay: 1500, statusCode: 200, body: mvgDepartures() });
      },
    );
    openSpa();

    // Nothing to show yet: the screen names the calls that are running ...
    cy.get("#departures", { timeout: 10000 }).should(
      "contain",
      "Fetching 2 stops…",
    );
    // ... and counts the ones already answered.
    cy.get("#departures", { timeout: 10000 }).should(
      "contain",
      "1 of 2 stops ok",
    );
    cy.get("#departures .departure-row", { timeout: 15000 }).should(
      "have.length.at.least",
      1,
    );
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

  it("follows the configured retry budget", () => {
    const attemptCounts = {};

    stubStationLookups();
    stubDepartures({
      failingStops: [STOP_THAT_FAILS],
      attemptCounts,
    });
    openSpa(CONFIG_TOML_SINGLE_ATTEMPT);

    cy.get("#departures", { timeout: 15000 }).should(
      "contain",
      "No data (refresh failed)",
    );

    cy.then(() => {
      expect(attemptCounts[STOP_THAT_FAILS]).to.equal(1);
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
      .should("contain", "No answer from Balanstr.");
  });

  it("keeps the last departures of a stop that stops answering, greyed out", () => {
    stubStationLookups();
    const answers = {};
    cy.intercept(
      { method: "GET", url: "**/api/bgw-pt/v3/departures*" },
      (request) => {
        const globalId = new URL(request.url).searchParams.get("globalId");
        answers[globalId] = (answers[globalId] ?? 0) + 1;

        // The first cycle answers; from then on the stop is down.
        if (answers[globalId] > 1) {
          request.reply({ statusCode: 503, body: "Service Unavailable" });
          return;
        }
        request.reply({ statusCode: 200, body: mvgDepartures() });
      },
    );
    openSpa(CONFIG_TOML_SINGLE_ATTEMPT);

    rowsOf("Balanstr.")
      .should("have.length.at.least", 1)
      .and("not.have.class", "stale");

    refreshAtOnce();

    // The stop that answered is fresh ...
    rowsOf("Giesing").first().should("not.have.class", "stale");
    // ... the one that stopped answering keeps its rows, greyed out ...
    rowsOf("Balanstr.")
      .first()
      .should("have.class", "stale")
      // ... and greyed out only: a strikethrough means cancelled.
      .and("not.have.class", "cancelled");
    // It does not claim to have nothing to show.
    cy.get("#departures").should("not.contain", "No data (refresh failed)");
  });

  it("announces the failures when there is nothing else to show", () => {
    stubStationLookups();
    stubDepartures({ failingStops: [STOP_WITH_DEPARTURES, STOP_THAT_FAILS] });
    openSpa();

    cy.get(".stop-failures", { timeout: 15000 })
      .should("be.visible")
      .and("contain", "No answer from 2 stops");
    cy.get("#api-status-container")
      .should("have.attr", "aria-label")
      .and("contain", "API status: error");
  });
});
