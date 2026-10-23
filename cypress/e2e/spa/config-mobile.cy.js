/**
 * The configuration dialogs are the product: they have to work with a thumb on
 * a phone, not just on a laptop. These specs drive every dialog at phone sizes -
 * the pages, raw TOML editing, the wizard, deleting a stop or a page, clean-up,
 * the Next to me row and the full-screen editor - and fail when a dialog is
 * wider than the screen or does not fit into its height.
 */
const CONFIG_TOML_KEY = "mvg_departures_config_toml";

const CONFIG_TOML = `
[display]
title = "Mobile e2e"
refresh_interval_seconds = 20

[[routes]]
path = "/"

[[routes.stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
show_ungrouped = true

[routes.stops.direction_mappings]
"->City" = ["U2 Messestadt"]

[[routes]]
path = "/work"

[[routes.stops]]
station_id = "de:09162:1056"
station_name = "Balanstr."
show_ungrouped = true
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

function openConfig(configToml = CONFIG_TOML) {
  cy.intercept("**/api/bgw-pt/v3/**", { statusCode: 200, body: [] });
  cy.visit("/", {
    onBeforeLoad(win) {
      win.localStorage.setItem(CONFIG_TOML_KEY, configToml);
    },
  });
  cy.get(".config-button").click();
  cy.get(".modal-content").should("be.visible");
}

/** The raw TOML is a tap away from the pages. */
function openTomlView() {
  cy.get(".view-tabs").contains("button", "TOML").click();
  cy.get(".config-textarea").should("be.visible");
}

/** Nothing may scroll sideways: that is what a dialog looks like when it breaks. */
function expectNoSidewaysScroll() {
  cy.document().then((doc) => {
    const page = doc.documentElement;
    expect(page.scrollWidth, "page width").to.be.at.most(page.clientWidth + 1);
  });
}

/** A dialog has to sit inside the screen, not hang over its edges. */
function expectFitsVertically(selector) {
  cy.get(selector).then(($element) => {
    const box = $element[0].getBoundingClientRect();
    const viewport = { top: 0, bottom: cy.state("viewportHeight") };
    expect(box.top, `${selector} top`).to.be.at.least(viewport.top - 1);
    expect(box.bottom, `${selector} bottom`).to.be.at.most(viewport.bottom + 1);
  });
}

/**
 * Fitting is not enough: the dialog exists to edit TOML, so the editor has to
 * get a useful share of the screen instead of a two-line sliver.
 */
function expectUsableEditor() {
  cy.get(".config-textarea").then(($element) => {
    const height = $element[0].getBoundingClientRect().height;
    const viewport = cy.state("viewportHeight");
    expect(height, "editor height").to.be.at.least(viewport * 0.3);
  });
}

describe("configuration dialogs on a phone", () => {
  beforeEach(() => {
    cy.viewport(...IPHONE);
  });

  it("shows the pages first and saves them from there", () => {
    openConfig();

    expectNoSidewaysScroll();
    expectFitsVertically(".modal-content");
    cy.get(".page-card").should("have.length", 2);
    cy.get(".page-card").first().should("contain", "Giesing");

    // A page's controls have to stay on screen, not slide out to the right.
    cy.get(".page-card")
      .first()
      .then(($card) => {
        const box = $card[0].getBoundingClientRect();
        expect(box.right, "page card right").to.be.at.most(cy.state("viewportWidth"));
      });
    cy.get(".page-actions").first().should("be.visible");

    openTomlView();
    expectUsableEditor();
    cy.get(".config-textarea").should("contain.value", "Giesing");

    cy.get(".modal-footer").contains("button", "Save").click();

    cy.get(".modal-content").should("not.exist");
    cy.window().its("localStorage").invoke("getItem", CONFIG_TOML_KEY).should("contain", "Mobile e2e");
  });

  it("expands the editor to the whole screen and comes back", () => {
    openConfig();
    openTomlView();

    cy.get('[aria-label="Expand editor"]').click();
    cy.get(".fullscreen-textarea").should("be.visible");
    expectFitsVertically(".fullscreen-editor-content");

    cy.get(".fullscreen-textarea").type("# typed on a phone");
    cy.contains("button", "Done").click();

    cy.get(".fullscreen-textarea").should("not.exist");
    cy.get(".config-textarea").should("contain.value", "# typed on a phone");
  });

  it("tweaks a value with the filter", () => {
    openConfig();
    openTomlView();

    cy.get('[aria-label="Tweak display values"]').click();
    cy.get(".tweak-filter-input").should("be.visible").type("title");
    cy.get(".tweak-section").should("have.length.at.least", 1);
    expectNoSidewaysScroll();

    cy.contains("button", "Ok").click();
    cy.get(".tweak-overlay").should("not.exist");
  });

  it("cleans up a config written for the server", () => {
    openConfig(LEGACY_TOML);
    openTomlView();

    cy.contains("button", "Clean up").click();
    cy.contains("button", "Apply clean-up").click();

    cy.get(".config-notice").should("be.visible").and("contain", "removed [api]");
    cy.get(".config-textarea").should("not.contain.value", "[api]");
    expectNoSidewaysScroll();
  });

  it("puts the Next to me page back", () => {
    openConfig();

    cy.get(".page-row").should("contain", "is missing from this config");
    cy.get(".page-row").contains("button", "Restore").click();

    cy.get(".page-row").should("contain", "is part of this config");
    cy.get(".page-row").should("not.contain", "Remove");
  });

  it("deletes a stop from a page", () => {
    openConfig();

    cy.get(".page-card").first().should("contain", "Giesing");
    cy.get('[aria-label="Delete Giesing"]').click();
    cy.get(".page-stop-confirm").contains("button", "Delete").click();

    cy.get(".page-card").first().should("not.contain", "Giesing");
    expectNoSidewaysScroll();
  });

  it("deletes a page only after confirming it", () => {
    openConfig();

    cy.get(".page-card").should("have.length", 2);
    cy.get(".page-card").eq(1).contains("button", "Delete page").click();
    cy.get(".page-card").eq(1).contains("button", "Keep page").click();
    cy.get(".page-card").should("have.length", 2);

    cy.get(".page-card").eq(1).contains("button", "Delete page").click();
    cy.get(".page-card").eq(1).contains("button", "Yes, delete").click();

    cy.get(".page-card").should("have.length", 1);
    cy.get(".page-card").first().should("not.contain", "/work");
  });

  it("edits a page in a form that fits the screen", () => {
    openConfig();

    cy.get(".page-card").first().contains("button", "Edit").click();

    cy.get(".page-form input").first().should("be.visible").clear().type("Zuhause");
    expectNoSidewaysScroll();

    cy.contains("button", "Apply changes").click();

    cy.get(".page-form").should("not.exist");
    cy.get(".page-card").first().should("contain", "Zuhause");
  });

  it("adds a heading to a stop without leaving the screen", () => {
    openConfig();

    cy.get(".page-card").first().should("contain", "1 heading");
    cy.get(".page-card").first().contains("button", "Edit").click();
    cy.get(".page-card").first().contains("button", "Add heading").click();

    cy.get(".page-form-direction-name").last().should("be.visible").type("->Stadtmitte");
    cy.get(".page-form-direction textarea").last().type("U2 Messestadt");
    expectNoSidewaysScroll();

    cy.contains("button", "Apply changes").click();
    cy.get(".page-card").first().should("contain", "2 headings");
  });

  it("adds a stop with the wizard", () => {
    openConfig();

    // Registered after `openConfig`, so it wins over that catch-all stub.
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

    cy.get(".add-stops").click();
    cy.get(".wizard-content").should("be.visible");
    expectNoSidewaysScroll();
    expectFitsVertically(".wizard-content");

    cy.get(".target-button").contains("Main").click();
    cy.get(".search-input").type("Marienplatz");
    cy.get(".search-button").click();

    cy.get(".stops-checklist .checkbox-item").first().click();
    cy.contains("button", "Next (1 selected)").click();
    cy.contains("button", "Create Configuration").click();

    cy.get(".page-card").first().should("contain", "Marienplatz");
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
      openConfig();

      expectNoSidewaysScroll();
      expectFitsVertically(".modal-content");
      cy.get(".page-card").first().should("be.visible");

      openTomlView();
      expectUsableEditor();

      // The way out has to be reachable with one thumb: tapping Save proves it.
      cy.get(".modal-footer").contains("button", "Save").click();
      cy.get(".modal-content").should("not.exist");
    });
  });
});
