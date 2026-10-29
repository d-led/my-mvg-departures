// ***********************************************
// This example commands.js shows you how to
// create various custom commands and overwrite
// existing commands.
//
// For more comprehensive examples of custom
// commands please read more here:
// https://on.cypress.io/custom-commands
// ***********************************************

/**
 * Wait for WebSocket connection to be established.
 * Checks the connection status indicator to ensure the app is connected.
 * @param {number} timeout - Timeout in milliseconds (default: 30000)
 */
Cypress.Commands.add("waitForConnection", (timeout = 30000) => {
  // Wait for the connection status element to exist
  cy.get("#connection-status", { timeout }).should("exist");

  // Wait for connection to be established by checking the data-connection-state attribute
  // It should change from "connecting" to "connected"
  cy.get("#connection-status", { timeout }).should(($el) => {
    const connectionState = $el.attr("data-connection-state");
    if (connectionState !== "connected") {
      throw new Error(`Connection not established. Current state: ${connectionState || "unknown"}`);
    }
  });

  // Also verify the connected icon is visible as a secondary check
  cy.get("#connection-status #connected-icon", { timeout }).should("be.visible");
});

/**
 * Wait for the departures section to be visible.
 * @param {number} timeout - Timeout in milliseconds (default: 10000)
 */
Cypress.Commands.add("waitForDepartures", (timeout = 10000) => {
  cy.get("#departures", { timeout }).should("be.visible");
});

/**
 * Assert that the main header displays the expected text.
 * @param {string} expectedText - Expected text in the header (default: "MVG Departures")
 */
Cypress.Commands.add("shouldDisplayMainHeader", (expectedText = "Departures") => {
  cy.get("h1").should("contain", expectedText);
});

/**
 * Assert that at least the minimum number of direction headers are displayed.
 * @param {number} minCount - Minimum number of direction headers (default: 1)
 * @param {number} timeout - Timeout in milliseconds (default: 10000)
 */
Cypress.Commands.add("shouldDisplayDirectionHeaders", (minCount = 1, timeout = 10000) => {
  cy.waitForDepartures(timeout);
  cy.get(".direction-header").should("have.length.at.least", minCount);
});

/**
 * Assert that the clock is displayed in the first header when departures are available.
 * If no clock exists (no departures), logs that this is acceptable.
 * @param {number} timeout - Timeout in milliseconds (default: 10000)
 */
Cypress.Commands.add("shouldDisplayClock", (timeout = 10000) => {
  cy.waitForDepartures(timeout);
  cy.get("body").then(($body) => {
    const clockExists = $body.find("#datetime-display").length > 0;
    if (clockExists) {
      cy.get("#datetime-display", { timeout: 3000 })
        .should("be.visible")
        .should(($el) => {
          const text = $el.text().trim();
          expect(text.length).to.be.greaterThan(0);
          expect(text).to.match(/\d{1,2}:\d{2}/);
        });
    } else {
      cy.log("No clock element - no departures available");
    }
  });
});

/**
 * Assert that the connection status indicator is visible with an icon.
 */
Cypress.Commands.add("shouldDisplayConnectionStatus", () => {
  cy.get("#connection-status").should("be.visible");
  cy.get("#connection-status").within(() => {
    cy.get("img").should("have.length.at.least", 1);
  });
});

/**
 * Assert that the API status indicator is visible with an icon.
 */
Cypress.Commands.add("shouldDisplayApiStatus", () => {
  cy.get("#api-status-container").should("be.visible");
  cy.get("#api-status-container").within(() => {
    cy.get("svg").should("have.length.at.least", 1);
  });
});

/**
 * Assert that the refresh countdown timer is visible.
 */
Cypress.Commands.add("shouldDisplayRefreshCountdown", () => {
  cy.get(".refresh-countdown").should("be.visible");
  cy.get(".refresh-countdown svg").should("be.visible");
});

/**
 * Assert that the presence count indicator is visible.
 */
Cypress.Commands.add("shouldDisplayPresenceCount", () => {
  cy.get("#presence-count").should("be.visible");
  cy.get("#presence-count .presence-icon").should("be.visible");
});

/**
 * Assert that departure information is displayed when available.
 * Either departure rows or a "no departures" message should be present.
 * @param {number} timeout - Timeout in milliseconds (default: 10000)
 */
Cypress.Commands.add("shouldDisplayDepartureInformation", (timeout = 10000) => {
  cy.waitForDepartures(timeout);
  cy.get("#departures").within(() => {
    cy.get(".departure-row, [role='status']").should("have.length.at.least", 1);
  });
});

/**
 * Assert that the page has accessible ARIA labels.
 */
Cypress.Commands.add("shouldHaveAccessibleAriaLabels", () => {
  cy.get("#departures").should("have.attr", "role", "region");
  cy.get("#departures").should("have.attr", "aria-label");
  cy.get("#aria-live-status").should("exist");
  cy.get("#aria-live-departures").should("exist");
});

/**
 * Assert that the status floating box is visible with all indicators.
 * @param {number} minItems - Minimum number of status items (default: 3)
 */
Cypress.Commands.add("shouldDisplayStatusFloatingBox", (minItems = 3) => {
  cy.get(".status-floating-box").should("be.visible");
  cy.get(".status-floating-box-item").should("have.length.at.least", minItems);
});

// *****************************************************************************
// The config dialog's Configurator: no spec selects into the dialog, everything
// it needs lives here.
// *****************************************************************************

const CONFIG_TOML_KEY = "mvg_departures_config_toml";

/** Opens the config dialog straight on the Configurator screen. */
Cypress.Commands.add("openConfigurator", () => {
  cy.get("body").then(($body) => {
    if ($body.find(".modal-content").length === 0) {
      cy.get(".config-button").click();
    }
  });
  cy.get(".config-method-selector").contains("button", "Configurator").click();
  cy.get(".cfg").should("exist");
});

/** Leaves the configurator; the file is untouched until Save. */
Cypress.Commands.add("closeConfigurator", () => {
  cy.get(".configurator-panel .modal-footer").contains("button", "Done").click();
  cy.get(".cfg").should("not.exist");
});

/** The configurator's Done and the dialog's Save, in one go. */
Cypress.Commands.add("saveConfigDialog", () => {
  cy.closeConfigurator();
  cy.saveConfig();
});

/** The TOML the dialog has stored, as the app will read it next time. */
Cypress.Commands.add("storedConfig", () => cy.window().its("localStorage").invoke("getItem", CONFIG_TOML_KEY));

/** The names of the routes, in the order they are listed. */
Cypress.Commands.add("configRouteNames", () =>
  cy.get(".cfg .page-row").then(($rows) => [...$rows].map((row) => (row.querySelector(".name")?.textContent ?? row.querySelector(".row-input")?.value ?? "").trim())),
);

/** The names of the stops of the open route; none is a valid answer. */
Cypress.Commands.add("configStopNames", () =>
  cy.get(".cfg").then(($cfg) => [...$cfg[0].querySelectorAll(".row.sub")].map((row) => (row.querySelector(".name")?.textContent ?? row.querySelector(".row-input")?.value ?? "").trim())),
);

/** Opens the route with that name; opening another closes the first. */
Cypress.Commands.add("openConfigRoute", (name) => {
  cy.get(".cfg .page-row").contains(".name", name).closest(".page-row").find('[data-role="page"]').click();
});

Cypress.Commands.add("openConfigStop", (name) => {
  cy.get(".cfg .row.sub").contains(".name", name).closest(".row").find('[data-role="stop"]').click();
});

/** A route opens by tapping its name, not only by its tiny triangle. */
Cypress.Commands.add("tapConfigRouteName", (name) => {
  cy.get(".cfg .page-row").contains(".name", name).click();
});

Cypress.Commands.add("tapConfigStopName", (name) => {
  cy.get(".cfg .row.sub").contains(".name", name).click();
});

Cypress.Commands.add("openConfigDirection", (index = 0) => {
  cy.get('.cfg [data-role="direction"]').eq(index).click();
});

Cypress.Commands.add("openConfigRouteSettings", () => {
  cy.get('.cfg [data-role="page-settings"]').click();
});

Cypress.Commands.add("openConfigDefaults", () => {
  cy.get('.cfg [data-role="defaults"]').click();
});

Cypress.Commands.add("addConfigRoute", () => {
  cy.get('.cfg [data-role="add-page"]').click();
});

Cypress.Commands.add("addConfigStop", () => {
  cy.get('.cfg [data-role="add-stop"]').click();
});

Cypress.Commands.add("addConfigDirection", () => {
  cy.get('.cfg [data-role="add-direction"]').click();
});

Cypress.Commands.add("deleteConfigRoute", (name) => {
  cy.get(`.cfg [aria-label="Delete the route ${name}"]`).click();
});

Cypress.Commands.add("confirmConfigRouteDeletion", (name) => {
  cy.get(".cfg").contains("button", `⨯ “${name}”`).click();
});

Cypress.Commands.add("deleteConfigStop", (name) => {
  cy.get(`.cfg [aria-label="Delete ${name}"]`).click();
});

Cypress.Commands.add("confirmConfigStopDeletion", (name) => {
  cy.get(".cfg").contains("button", `⨯ ${name}`).click();
});

/** A labelled field of the configurator, by its visible label. */
Cypress.Commands.add("configField", (label) => cy.get(".cfg .field").contains("span", label).parent().find("input"));

/** A select of the configurator by the label a screen reader hears. */
Cypress.Commands.add("configSelect", (ariaLabel) => cy.get(`.cfg select[aria-label="${ariaLabel}"]`));

/** A field of the configurator by the label a screen reader hears. */
Cypress.Commands.add("configInput", (ariaLabel) => cy.get(`.cfg input[aria-label="${ariaLabel}"]`));

/** The sections the open display form is read in. */
Cypress.Commands.add("configFieldSections", () => cy.get(".cfg .display-group h4"));

Cypress.Commands.add("configButton", (text) => cy.get(".cfg .button").contains(text));

Cypress.Commands.add("configProblem", () => cy.get(".cfg .problem"));

/** Replaces the whole content of a labelled field, without a separate clear. */
Cypress.Commands.add("retypeConfigInput", (ariaLabel, text) => {
  cy.get(`.cfg input[aria-label="${ariaLabel}"]`).clear().type(`${text}{enter}`);
});

Cypress.Commands.add("retypeConfigMatch", (index, text) => {
  cy.get('.cfg [data-role="match"] input').eq(index).clear().type(`${text}{enter}`);
});

Cypress.Commands.add("removeConfigMatch", (index = 0) => {
  cy.get('.cfg [data-role="match"] .icon-button').eq(index).click();
});

/** Reorders a route with the keyboard: Alt+Arrow on its grip. */
Cypress.Commands.add("moveConfigRouteWithKeyboard", (name, to) => {
  cy.get(".cfg .page-row")
    .contains(".name", name)
    .closest(".page-row")
    .find(".grip")
    .focus()
    .trigger("keydown", { key: to === "up" ? "ArrowUp" : "ArrowDown", altKey: true });
});

/** The editable matches of the open direction. */
Cypress.Commands.add("configMatches", () => cy.get('.cfg [data-role="match"] input'));

/** Drags one route onto another by its grip; Escape cancels the drag. */
Cypress.Commands.add("dragConfigRoute", (fromIndex, toIndex, options = {}) => {
  cy.get('.cfg [data-role="page"]').then(($rows) => {
    const from = $rows[fromIndex].getBoundingClientRect();
    const to = $rows[toIndex].getBoundingClientRect();
    const at = { clientX: to.left + 5, clientY: to.top + to.height / 2 };

    cy.wrap($rows[fromIndex])
      .parent()
      .find(".grip")
      .trigger("pointerdown", {
        which: 1,
        clientX: from.left + 5,
        clientY: from.top + 5,
      });
    cy.window().trigger("pointermove", at);
    if (options.cancel) {
      cy.window().trigger("keydown", { key: "Escape" });
    }
    cy.window().trigger("pointerup", at);
  });
});

Cypress.Commands.add("searchConfigStop", (name) => {
  cy.get('.cfg input[aria-label="Search a stop to add"]').type(name);
  cy.get(".cfg").contains("button", "Search").click();
});

Cypress.Commands.add("pickConfigStop", (name) => {
  cy.get(".cfg .form .row.sub").contains(name).click();
});

/** Declines the delete the configurator asked about. */
Cypress.Commands.add("cancelConfigRouteDeletion", () => {
  cy.get(".cfg .actions").contains("button", "Keep").click();
});

// *****************************************************************************
// The config dialog's other screens, and the way a phone sees them.
// *****************************************************************************

/** Opens the config dialog on the page it is already showing. */
Cypress.Commands.add("openConfigButton", () => {
  cy.get(".config-button").click();
  cy.get(".modal-content").should("be.visible");
});

/** The dialog as a whole, whatever screen it is showing. */
Cypress.Commands.add("dialogContent", () => cy.get(".modal-content"));

Cypress.Commands.add("dialogClosed", () => cy.get(".modal-content").should("not.exist"));

/** The dialog's mode row. */
Cypress.Commands.add("configTabs", () => cy.get(".config-method-selector .method-button"));

/** A button in the dialog's own footer, not the configurator's. */
Cypress.Commands.add("footerButton", (text) => cy.get(".modal-footer").contains("button", text));

/** The configurator's rows. */
Cypress.Commands.add("configPanel", () => cy.get(".cfg"));

Cypress.Commands.add("mainHeadline", () => cy.get("h1"));

Cypress.Commands.add("appBody", () => cy.get("body"));

/** Opens the config dialog on a stored TOML, as the app would find it. */
Cypress.Commands.add("openConfigDialog", (toml, hash = "/") => {
  cy.intercept("**/api/bgw-pt/v3/**", { statusCode: 200, body: [] });
  cy.visit(hash, {
    onBeforeLoad(win) {
      win.localStorage.setItem(CONFIG_TOML_KEY, toml);
    },
  });
  cy.get(".config-button").click();
  cy.get(".modal-content").should("be.visible");
});

/** The file as text. */
Cypress.Commands.add("tomlEditor", () => cy.get(".config-textarea"));

/** The TOML Config tab: the file is edited where it is. */
Cypress.Commands.add("openTomlView", () => {
  cy.get(".config-method-selector").contains("button", "TOML Config").click();
  cy.get(".config-textarea").should("be.visible");
});

/** Saves the dialog; the file is stored and the dialog closes. */
Cypress.Commands.add("saveConfig", () => {
  cy.get(".modal-footer").contains("button", "Save").click();
  cy.get(".modal-content").should("not.exist");
});

/** Asks the dialog to close, without saying what to do with unsaved edits. */
Cypress.Commands.add("cancelConfigDialog", () => {
  cy.get(".modal-footer").contains("button", "Cancel").click();
});

Cypress.Commands.add("keepEditing", () => {
  cy.get(".discard-question").parent().contains("button", "Keep editing").click();
});

Cypress.Commands.add("discardChanges", () => {
  cy.get(".discard-question").parent().contains("button", "Discard changes").click();
  cy.get(".modal-content").should("not.exist");
});

/** The editor blown up to the whole screen, for a phone keyboard. */
Cypress.Commands.add("expandTomlEditor", () => {
  cy.get('[aria-label="Expand editor"]').click();
  cy.get(".fullscreen-textarea").should("be.visible");
});

Cypress.Commands.add("fullscreenEditor", () => cy.get(".fullscreen-textarea"));

Cypress.Commands.add("closeFullscreenEditor", () => {
  cy.get(".fullscreen-editor-content").contains("button", "Done").click();
  cy.get(".fullscreen-textarea").should("not.exist");
});

/** The numeric values, one overlay over the file. */
Cypress.Commands.add("openTweaks", () => {
  cy.get('[aria-label="Tweak display values"]').click();
  cy.get(".tweak-filter-input").should("be.visible");
});

Cypress.Commands.add("filterTweaks", (text) => cy.get(".tweak-filter-input").type(text));

Cypress.Commands.add("tweakSections", () => cy.get(".tweak-section"));

Cypress.Commands.add("closeTweaks", () => {
  cy.get(".tweak-overlay").contains("button", "Ok").click();
  cy.get(".tweak-overlay").should("not.exist");
});

/** The clean-up: a command, never a side effect of looking at a screen. */
Cypress.Commands.add("cleanUpConfig", () => {
  cy.get(".config-method-selector").contains("button", "Clean up").click();
});

/** The configurator's own offer to turn a server-format file into routes. */
Cypress.Commands.add("convertConfigToRoutes", () => {
  cy.get('.cfg [data-role="convert"]').click();
});

Cypress.Commands.add("cleanUpReview", () => cy.get(".cleanup-review"));

Cypress.Commands.add("applyCleanUp", () => cy.get(".cleanup-review").contains("button", "Apply clean-up").click());

Cypress.Commands.add("cancelCleanUp", () => cy.get(".cleanup-review").contains("button", "Cancel clean-up").click());

Cypress.Commands.add("configNotice", () => cy.get(".config-notice"));

/** The Next to me page: the row above the routes, and its form. */
Cypress.Commands.add("nextToMeRow", () => cy.contains(".page-row", "Next to me"));

Cypress.Commands.add("restoreNextToMePage", () => cy.nextToMeRow().contains("button", "Restore").click());

Cypress.Commands.add("editNextToMePage", () => cy.nextToMeRow().contains("button", "Edit").click());

Cypress.Commands.add("nextToMeField", (label) => cy.get(`.on-the-run-field input[aria-label="${label}"]`));

Cypress.Commands.add("applyNextToMeForm", () => cy.contains(".page-row-form button", "Apply").click());

Cypress.Commands.add("nextToMeForm", () => cy.get(".page-row-form"));

/** The dialog's other screens: the wizard and the two ways of deleting. */
Cypress.Commands.add("openWizard", () => {
  cy.get(".config-method-selector").contains("button", "Wizard").click();
  cy.get(".wizard-content").should("be.visible");
});

Cypress.Commands.add("openHeaderDeletion", () => {
  cy.get(".config-method-selector").contains("button", "Delete (current route)").click();
});

Cypress.Commands.add("openRouteDeletion", () => {
  cy.get(".config-method-selector").contains("button", "Routes").click();
});

Cypress.Commands.add("headerDeletionItems", () => cy.get(".delete-list .delete-item"));

Cypress.Commands.add("routeDeletionItems", () => cy.get(".delete-routes-list .delete-item"));

Cypress.Commands.add("routeDeletionHint", () => cy.get(".delete-routes-hint"));

Cypress.Commands.add("reviewDeletion", () => cy.get(".modal-footer").contains("button", "Review Delete").click());

Cypress.Commands.add("reviewDeletionButton", () => cy.get(".modal-footer").contains("button", "Review Delete"));

Cypress.Commands.add("confirmDeletion", () => cy.get(".modal-footer").contains("button", "Confirm Delete").click());

/** The wizard, opened from the configurator to add stops to a route. */
Cypress.Commands.add("openStopWizard", () => {
  cy.configButton("Wizard").click();
  cy.get(".wizard-content").should("be.visible");
});

Cypress.Commands.add("wizardPickMain", () => cy.get(".target-button").contains("Main").click());

Cypress.Commands.add("wizardSearchStop", (name) => {
  cy.get(".search-input").type(name);
  cy.get(".search-button").click();
});

Cypress.Commands.add("wizardPickFirstStop", () => cy.get(".stops-checklist .checkbox-item").first().click());

Cypress.Commands.add("wizardNext", () => cy.contains("button", /^Next \(/).click());

Cypress.Commands.add("wizardCreate", () => cy.contains("button", "Create Configuration").click());

/**
 * A phone shows one screen at a time: nothing may hang over an edge, and a
 * control has to be big enough for a thumb.
 */
Cypress.Commands.add("expectNoSidewaysScroll", () => {
  cy.document().then((doc) => {
    const page = doc.documentElement;
    expect(page.scrollWidth, "page width").to.be.at.most(page.clientWidth + 1);
  });
});

Cypress.Commands.add("expectInsideViewport", (selector) => {
  cy.get(selector)
    .first()
    .then(($element) => {
      const box = $element[0].getBoundingClientRect();
      expect(box.top, `${selector} top`).to.be.at.least(-1);
      expect(box.right, `${selector} right`).to.be.at.most(cy.state("viewportWidth") + 1);
      expect(box.bottom, `${selector} bottom`).to.be.at.most(cy.state("viewportHeight") + 1);
    });
});

/** Fitting is not enough: the file has to get a usable share of the screen. */
Cypress.Commands.add("expectTomlEditorUsable", () => {
  cy.get(".config-textarea").then(($element) => {
    const height = $element[0].getBoundingClientRect().height;
    expect(height, "editor height").to.be.at.least(cy.state("viewportHeight") * 0.3);
  });
});

Cypress.Commands.add("expectTapTarget", (selector, minSize = 32) => {
  cy.get(selector)
    .first()
    .should(($element) => {
      const box = $element[0].getBoundingClientRect();
      expect(box.width, `${selector} width`).to.be.at.least(minSize);
      expect(box.height, `${selector} height`).to.be.at.least(minSize);
    });
});
