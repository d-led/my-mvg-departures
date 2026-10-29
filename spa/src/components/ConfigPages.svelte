<script lang="ts">
  /* global HTMLInputElement, PointerEvent */
  import { SvelteMap } from "svelte/reactivity";
  import DisplayFields from "./DisplayFields.svelte";
  import {
    draftOfSettings,
    settingsOfDraft,
    type ConfigDirectionMapping,
    type ConfigPage,
    type ConfigPageEdit,
    type ConfigPageStop,
    type ConfigPageStopEdit,
    type DisplayDraft,
    type DisplaySettings,
    type NewConfigPage,
    type NewConfigStop,
  } from "../utils/config-pages.js";
  import { MvgStationRepository } from "../adapters/mvg/mvg-station-repository.js";
  import { CompositeDepartureRepository } from "../adapters/composite-departure-repository.js";
  import {
    createStopConfiguration,
    type StopConfiguration,
  } from "../domain/models/stop-configuration.js";
  import {
    destinationPattern,
    linePattern,
    observedLines,
    type ObservedLine,
  } from "../application/services/observed-lines.js";

  let {
    pages,
    defaults,
    onReorder,
    onRemovePage,
    onRemoveStop,
    onApplyPage,
    onApplyStop,
    onApplyPageDisplay,
    onApplyDefaults,
    onAddPage,
    onAddStop,
    onAddStops,
    onConvert,
  }: {
    pages: ConfigPage[];
    /** The file's own display settings, which every page inherits. */
    defaults: DisplaySettings;
    onReorder: (from: number, to: number) => void;
    onRemovePage: (index: number) => void;
    onRemoveStop: (pageIndex: number, stopIndex: number) => void;
    onApplyPage: (index: number, edit: ConfigPageEdit) => void;
    onApplyStop: (
      pageIndex: number,
      stopIndex: number,
      edit: ConfigPageStopEdit,
    ) => void;
    onApplyPageDisplay: (index: number, values: DisplaySettings) => void;
    onApplyDefaults: (values: DisplaySettings) => void;
    onAddPage: (page: NewConfigPage) => void;
    onAddStop: (pageIndex: number, stop: NewConfigStop) => void;
    onAddStops: () => void;
    /** Turns a server-format file's stops into routes, as a reviewable edit. */
    onConvert: () => void;
  } = $props();

  /**
   * One context at a time: a page, one of its stops, one of that stop's
   * headings, or one form. Opening one closes the others, so the dialog never
   * grows into a wall of fields on a phone.
   */
  let openPage = $state<number | null>(null);
  let openStop = $state<number | null>(null);
  let openHeading = $state<number | null>(null);
  let openForm = $state<"page" | "defaults" | "add-stop" | "new-page" | null>(
    null,
  );
  /** What is being deleted: "page:0", "stop:0:1". */
  let confirming = $state<string | null>(null);

  /** A page drag in flight: where it started, and where it would land. */
  let dragFrom = $state<number | null>(null);
  let dragOver = $state<number | null>(null);

  function pageRows(): HTMLElement[] {
    return [...document.querySelectorAll<HTMLElement>('[data-role="page"]')];
  }

  /**
   * Dragging a page by its grip. Nothing moves until the pointer is released, and
   * Escape or a cancelled pointer leaves the order exactly as it was.
   */
  function startDrag(event: PointerEvent, index: number) {
    event.preventDefault();
    dragFrom = index;
    dragOver = index;

    const move = (moveEvent: PointerEvent) => {
      const row = pageRows().find((each) => {
        const rect = each.getBoundingClientRect();
        return (
          moveEvent.clientY >= rect.top && moveEvent.clientY <= rect.bottom
        );
      });
      const at =
        row?.dataset.index === undefined ? NaN : Number(row.dataset.index);
      if (Number.isInteger(at)) {
        dragOver = at;
      }
    };

    const finish = (commit: boolean) => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", drop);
      window.removeEventListener("pointercancel", abort);
      window.removeEventListener("keydown", escape);
      const from = dragFrom;
      const to = dragOver;
      dragFrom = null;
      dragOver = null;
      if (commit && from !== null && to !== null && from !== to) {
        onReorder(from, to);
      }
    };

    const drop = () => finish(true);
    const abort = () => finish(false);
    const escape = (keyEvent: KeyboardEvent) => {
      if (keyEvent.key === "Escape") {
        finish(false);
      }
    };

    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", drop);
    window.addEventListener("pointercancel", abort);
    window.addEventListener("keydown", escape);
  }

  /** The line whose destinations are shown, and the filter over the lines. */
  let openLine = $state<string | null>(null);
  let lineFilter = $state("");

  let pageDraft = $state<{
    path: string;
    title: string;
    settings: DisplayDraft;
  } | null>(null);
  let defaultsDraft = $state<DisplayDraft | null>(null);
  let newPageDraft = $state<{ path: string; title: string } | null>(null);

  let stopQuery = $state("");
  let stopMatches = $state<NewConfigStop[]>([]);
  let isSearchingStops = $state(false);
  let stopSearchProblem = $state("");

  /** The lines each stop's departures showed, by station id. */
  const linesByStop = new SvelteMap<string, ObservedLine[]>();
  const linesLoading = new SvelteMap<string, boolean>();
  const linesProblem = new SvelteMap<string, string>();

  const searchableStations = new MvgStationRepository();

  /** What an unset key means: the domain's own defaults, shown in the fields. */
  const stopDefaults: StopConfiguration = createStopConfiguration({
    stationId: "",
    stationName: "",
  });

  // A page or a stop that just went away must not leave its context open.
  $effect(() => {
    if (openPage !== null && openPage >= pages.length) {
      openPage = null;
      openStop = null;
      openHeading = null;
    }
    const stops = openPage === null ? undefined : pages[openPage]?.stops;
    if (stops && openStop !== null && openStop >= stops.length) {
      openStop = null;
      openHeading = null;
    }
  });

  function togglePage(index: number) {
    const opening = openPage !== index;
    openPage = opening ? index : null;
    openStop = null;
    openHeading = null;
    confirming = null;
    if (!opening) {
      openForm = null;
    }
  }

  function toggleStop(index: number, stop: ConfigPageStop) {
    const opening = openStop !== index;
    openStop = opening ? index : null;
    openHeading = null;
    openForm = null;
    openLine = null;
    lineFilter = "";
    confirming = null;
    if (opening) {
      void loadLines(stop);
    }
  }

  function toggleHeading(index: number) {
    openHeading = openHeading === index ? null : index;
    openLine = null;
    lineFilter = "";
  }

  function toggleForm(form: "page" | "defaults" | "add-stop" | "new-page") {
    const opening = openForm !== form;
    openForm = opening ? form : null;
    confirming = null;
    if (!opening) {
      pageDraft = null;
      defaultsDraft = null;
      newPageDraft = null;
    }
  }

  /* ---- the page's own form ---- */

  function openPageForm(page: ConfigPage) {
    pageDraft = {
      path: page.path,
      title: page.title,
      settings: draftOfSettings(page.display),
    };
    toggleForm("page");
  }

  /** Why the draft cannot be applied, or "" while it can. */
  const pathProblem = $derived.by(() => {
    const draft = pageDraft;
    if (draft === null || openPage === null) {
      return "";
    }
    const path = draft.path.trim();
    if (!path.startsWith("/")) {
      return "A path starts with a slash, like /work.";
    }
    return pages.some((page, at) => at !== openPage && page.path === path)
      ? "Another page already uses this path."
      : "";
  });

  /**
   * Only the page's own text and settings: the stops are edited where they are
   * shown, so this form leaves their headings exactly as they are.
   */
  function applyPageDraft(index: number) {
    if (pageDraft === null || pathProblem !== "") {
      return;
    }
    const edit: ConfigPageEdit = {
      path: pageDraft.path.trim(),
      title: pageDraft.title,
      stops: pages[index].stops.map((stop) => ({
        label: stop.label,
        showUngrouped: stop.showUngrouped,
      })),
    };
    const settings = settingsOfDraft(pageDraft.settings);
    openForm = null;
    pageDraft = null;
    onApplyPage(index, edit);
    onApplyPageDisplay(index, settings);
  }

  function applyDefaults() {
    if (defaultsDraft === null) {
      return;
    }
    const values = settingsOfDraft(defaultsDraft);
    defaultsDraft = null;
    openForm = null;
    onApplyDefaults(values);
  }

  /* ---- a stop ---- */

  function applyStop(
    pageIndex: number,
    stopIndex: number,
    stop: ConfigPageStop,
    change: Partial<ConfigPageStopEdit>,
  ) {
    onApplyStop(pageIndex, stopIndex, {
      label: stop.label,
      showUngrouped: stop.showUngrouped,
      directions: stop.directions,
      ...change,
    });
  }

  /** The stop's headings with the one at `headingIndex` replaced. */
  function withHeading(
    stop: ConfigPageStop,
    headingIndex: number,
    heading: ConfigDirectionMapping,
  ): ConfigDirectionMapping[] {
    return stop.directions.map((existing, at) =>
      at === headingIndex ? heading : existing,
    );
  }

  function addHeading(
    pageIndex: number,
    stopIndex: number,
    stop: ConfigPageStop,
  ) {
    openHeading = stop.directions.length;
    // A direction without a name would be dropped on the way into the file, so a
    // new one starts with a name that says what it is until it is renamed.
    applyStop(pageIndex, stopIndex, stop, {
      directions: [
        ...stop.directions,
        { direction: `->${stop.directions.length + 1}`, patterns: [] },
      ],
    });
  }

  function removeHeading(
    pageIndex: number,
    stopIndex: number,
    stop: ConfigPageStop,
    headingIndex: number,
  ) {
    openHeading = null;
    applyStop(pageIndex, stopIndex, stop, {
      directions: stop.directions.filter((_, at) => at !== headingIndex),
    });
  }

  /** A heading keeps its matches when it is renamed. */
  function renameHeading(
    pageIndex: number,
    stopIndex: number,
    stop: ConfigPageStop,
    headingIndex: number,
    name: string,
  ) {
    const heading = stop.directions[headingIndex];
    if (name.trim() === "" || name === heading.direction) {
      return;
    }
    applyStop(pageIndex, stopIndex, stop, {
      directions: withHeading(stop, headingIndex, {
        ...heading,
        direction: name,
      }),
    });
  }

  /**
   * A direction is a filter, and its matches are plain text: adding one takes
   * the text as given ("18", "18 Stachus", "Stachus"), editing one rewrites
   * just that line, and an emptied match is dropped.
   */
  function showMatches() {
    requestAnimationFrame(() => {
      document
        .querySelector('[data-role="matches"]')
        ?.scrollIntoView({ block: "nearest" });
    });
  }

  function addMatch(
    pageIndex: number,
    stopIndex: number,
    stop: ConfigPageStop,
    headingIndex: number,
    text: string,
  ) {
    const pattern = text.trim();
    const heading = stop.directions[headingIndex];
    if (pattern === "" || heading.patterns.includes(pattern)) {
      return;
    }
    applyStop(pageIndex, stopIndex, stop, {
      directions: withHeading(stop, headingIndex, {
        ...heading,
        patterns: [...heading.patterns, pattern],
      }),
    });
    showMatches();
  }

  function setMatch(
    pageIndex: number,
    stopIndex: number,
    stop: ConfigPageStop,
    headingIndex: number,
    patternIndex: number,
    text: string,
  ) {
    const heading = stop.directions[headingIndex];
    const pattern = text.trim();
    if (pattern === "" || pattern === heading.patterns[patternIndex]) {
      return;
    }
    applyStop(pageIndex, stopIndex, stop, {
      directions: withHeading(stop, headingIndex, {
        ...heading,
        patterns: heading.patterns.map((existing, at) =>
          at === patternIndex ? pattern : existing,
        ),
      }),
    });
  }

  function removeMatch(
    pageIndex: number,
    stopIndex: number,
    stop: ConfigPageStop,
    headingIndex: number,
    patternIndex: number,
  ) {
    const heading = stop.directions[headingIndex];
    applyStop(pageIndex, stopIndex, stop, {
      directions: withHeading(stop, headingIndex, {
        ...heading,
        patterns: heading.patterns.filter((_, at) => at !== patternIndex),
      }),
    });
  }

  function addTypedMatch(
    pageIndex: number,
    stopIndex: number,
    stop: ConfigPageStop,
    headingIndex: number,
    input: HTMLInputElement,
  ) {
    const text = input.value;
    input.value = "";
    addMatch(pageIndex, stopIndex, stop, headingIndex, text);
  }

  /** A count from a form field: `null` empties it, `undefined` is not a number. */
  function countFrom(text: string): number | null | undefined {
    const trimmed = text.trim();
    if (trimmed === "") {
      return null;
    }
    const value = Number(trimmed);

    return Number.isInteger(value) && value >= 0 ? value : undefined;
  }

  type CountField = "maxDepartures" | "perLineDepartures" | "hoursInAdvance";

  function applyCount(
    pageIndex: number,
    stopIndex: number,
    stop: ConfigPageStop,
    field: CountField,
    input: HTMLInputElement,
  ) {
    const value = countFrom(input.value);
    if (value === undefined) {
      input.value = String(stop[field] ?? "");
      return;
    }
    if (value === (stop[field] ?? null)) {
      return;
    }
    if (field === "maxDepartures") {
      applyStop(pageIndex, stopIndex, stop, { maxDepartures: value });
    } else if (field === "perLineDepartures") {
      applyStop(pageIndex, stopIndex, stop, { perLineDepartures: value });
    } else {
      applyStop(pageIndex, stopIndex, stop, { hoursInAdvance: value });
    }
  }

  /* ---- the lines a stop's departures showed ---- */

  /**
   * The API is asked once per stop: its departures say which lines can be
   * matched, and one pattern for a line is enough when its destinations do not
   * matter. A stop the API cannot answer for keeps the matches typed by hand.
   */
  async function loadLines(stop: ConfigPageStop) {
    const id = stop.stationId;
    if (id === "" || linesByStop.has(id) || linesLoading.get(id) === true) {
      return;
    }

    linesLoading.set(id, true);
    linesProblem.delete(id);
    try {
      const departures = await new CompositeDepartureRepository([
        createStopConfiguration({ stationId: id, stationName: stop.name }),
      ]).getDepartures(id, { limit: 100 });
      linesByStop.set(id, observedLines(departures));
    } catch (error) {
      linesProblem.set(
        id,
        error instanceof Error ? error.message : String(error),
      );
    } finally {
      linesLoading.delete(id);
    }
  }

  function linesShownFor(stop: ConfigPageStop): ObservedLine[] {
    return linesByStop.get(stop.stationId) ?? [];
  }

  /** The stop's lines that the filter box leaves - a big stop needs one. */
  function shownLines(stop: ConfigPageStop): ObservedLine[] {
    const filter = lineFilter.trim().toLowerCase();
    const lines = linesShownFor(stop);
    if (filter === "") {
      return lines;
    }

    return lines.filter(
      (line) =>
        line.line.toLowerCase().includes(filter) ||
        line.destinations.some((destination) =>
          destination.toLowerCase().includes(filter),
        ),
    );
  }

  /* ---- adding a stop ---- */

  function openStopSearch() {
    stopQuery = "";
    stopMatches = [];
    stopSearchProblem = "";
    toggleForm("add-stop");
  }

  async function searchStops() {
    if (stopQuery.trim() === "") {
      return;
    }
    isSearchingStops = true;
    stopSearchProblem = "";
    try {
      const stations = await searchableStations.searchStations(stopQuery);
      stopMatches = stations.map((station) => ({
        stationId: station.id,
        stationName: station.name,
      }));
      stopSearchProblem =
        stopMatches.length === 0
          ? `No stop matches “${stopQuery.trim()}”.`
          : "";
    } catch (error) {
      stopSearchProblem =
        error instanceof Error ? error.message : String(error);
    } finally {
      isSearchingStops = false;
    }
  }

  function addStop(pageIndex: number, stop: NewConfigStop) {
    openForm = null;
    stopMatches = [];
    stopQuery = "";
    onAddStop(pageIndex, stop);
  }

  /* ---- a new page ---- */

  const newPageProblem = $derived.by(() => {
    const draft = newPageDraft;
    if (draft === null) {
      return "";
    }
    const path = draft.path.trim();
    if (!path.startsWith("/")) {
      return "A path starts with a slash, like /work.";
    }
    return pages.some((page) => page.path === path)
      ? "A page already uses this path."
      : "";
  });

  const canCreatePage = $derived(
    newPageDraft !== null &&
      newPageDraft.path.trim() !== "" &&
      newPageProblem === "",
  );

  function openNewPage() {
    newPageDraft = { path: "", title: "" };
    toggleForm("new-page");
  }

  function applyNewPage() {
    if (newPageDraft === null || !canCreatePage) {
      return;
    }
    const page: NewConfigPage = {
      path: newPageDraft.path.trim(),
      title: newPageDraft.title.trim(),
    };
    newPageDraft = null;
    openForm = null;
    onAddPage(page);
  }

  /* ---- what the rows say ---- */

  /** The route's supporting line: how much it holds, and where it lives. */
  function pageSummary(page: ConfigPage): string {
    const count = page.stops.length;
    const stops = `${count} stop${count === 1 ? "" : "s"}`;

    return page.path === page.title ? stops : `${stops} · ${page.path}`;
  }

  function stopSummary(stop: ConfigPageStop): string {
    const count = stop.directions.length;

    return count === 0
      ? "no directions"
      : `${count} direction${count === 1 ? "" : "s"}`;
  }

  /** How many settings the defaults actually set, in the file's own words. */
  function settingsSummary(settings: DisplaySettings): string {
    const count = Object.keys(settings).length;

    return count === 0
      ? "nothing set here"
      : `${count} setting${count === 1 ? "" : "s"} set here`;
  }

  function headingTitle(heading: ConfigDirectionMapping): string {
    return heading.direction.trim() === "" ? "(unnamed)" : heading.direction;
  }

  function headingSummary(heading: ConfigDirectionMapping): string {
    const count = heading.patterns.length;

    return `${count} match${count === 1 ? "" : "es"}`;
  }
</script>

<!-- Heroicons, 20/solid "chevron-right" and "plus" (MIT) - the same set the
     dialog's toolbar icons come from. The size sits in attributes because a
     snippet's <svg> carries no scope class of this component, so a scoped CSS
     width would never reach it. -->
{#snippet chevron(open: boolean)}
  <svg
    class="chevron"
    class:chevron-open={open}
    width="20"
    height="20"
    viewBox="0 0 20 20"
    fill="currentColor"
    aria-hidden="true"
  >
    <path
      fill-rule="evenodd"
      d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
      clip-rule="evenodd"
    />
  </svg>
{/snippet}

{#snippet plus()}
  <svg
    class="chevron"
    width="20"
    height="20"
    viewBox="0 0 20 20"
    fill="currentColor"
    aria-hidden="true"
  >
    <path
      d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z"
    />
  </svg>
{/snippet}

<div class="cfg">
  <ul class="rows">
    {#each pages as page, pageIndex (pageIndex)}
      <li>
        {#if page.legacy}
          <!-- The board reads the top-level stops as the route at "/", so they
               are listed here - read only, because editing one means turning it
               into a route first, and that is a conversion, not a keystroke. -->
          <div class="page-row">
            <div class="row-open is-static">
              <span class="row-text">
                <span class="name">{page.title}</span>
                <span class="meta">{pageSummary(page)} · server format</span>
              </span>
            </div>
          </div>
          <div class="children">
            <p class="note">
              Stops outside any route, the way the server version wants them.
              The board shows them as “/”. Converting rewrites them as
              [[routes]], and you see the result before anything changes.
            </p>
            {#each page.stops as stop, stopIndex (stopIndex)}
              <div class="row sub">
                <div class="row-open is-static">
                  <span class="row-text">
                    <span class="name">{stop.name}</span>
                    <span class="meta">{stopSummary(stop)}</span>
                  </span>
                </div>
              </div>
            {/each}
            <div class="actions">
              <button
                class="button button-secondary"
                data-role="convert"
                onclick={onConvert}
              >
                Convert to routes…
              </button>
            </div>
          </div>
        {:else}
          <div
            class="page-row"
            class:dragging={dragFrom === pageIndex}
            class:drop-target={dragOver === pageIndex &&
              dragFrom !== null &&
              dragFrom !== pageIndex}
          >
            <span
              class="grip"
              role="button"
              tabindex="0"
              aria-label={`Reorder ${page.title}`}
              onpointerdown={(event) => startDrag(event, pageIndex)}
              onkeydown={(event) => {
                if (!event.altKey) {
                  return;
                }
                const to =
                  event.key === "ArrowUp" ? pageIndex - 1 : pageIndex + 1;
                if (
                  (event.key === "ArrowUp" || event.key === "ArrowDown") &&
                  to >= 0 &&
                  to < pages.length
                ) {
                  event.preventDefault();
                  onReorder(pageIndex, to);
                }
              }}>⠿</span
            >
            <button
              class="row-open"
              data-role="page"
              data-index={pageIndex}
              aria-expanded={openPage === pageIndex}
              onclick={() => togglePage(pageIndex)}
            >
              <span class="row-text">
                <span class="name">{page.title}</span>
                <span class="meta">{pageSummary(page)}</span>
              </span>
              {@render chevron(openPage === pageIndex)}
            </button>
          </div>

          {#if openPage === pageIndex}
            <div class="children">
              {#if openForm === "page" && pageDraft}
                <div class="form">
                  <label class="field">
                    <span>Title</span>
                    <input
                      bind:value={pageDraft.title}
                      placeholder={page.path}
                      aria-label="Route title"
                    />
                  </label>
                  <label class="field">
                    <span>Path</span>
                    <input
                      bind:value={pageDraft.path}
                      aria-label="Route path"
                      aria-invalid={pathProblem !== ""}
                    />
                  </label>
                  {#if pathProblem}
                    <p class="problem" role="alert">{pathProblem}</p>
                  {/if}
                  <DisplayFields draft={pageDraft.settings} />
                  <div class="actions">
                    <button
                      class="button button-secondary"
                      onclick={() => toggleForm("page")}>Cancel</button
                    >
                    <button
                      class="button button-primary"
                      disabled={pathProblem !== ""}
                      onclick={() => applyPageDraft(pageIndex)}
                    >
                      Apply
                    </button>
                  </div>
                </div>
              {/if}

              {#each page.stops as stop, stopIndex (stopIndex)}
                <div class="row sub">
                  <button
                    class="row-open"
                    data-role="stop"
                    aria-expanded={openStop === stopIndex}
                    onclick={() => toggleStop(stopIndex, stop)}
                  >
                    <span class="row-text">
                      <span class="name">{stop.name}</span>
                      <span class="meta">{stopSummary(stop)}</span>
                    </span>
                    {@render chevron(openStop === stopIndex)}
                  </button>
                </div>

                {#if openStop === stopIndex}
                  <div class="children">
                    <label class="field">
                      <span>Name</span>
                      <input
                        value={stop.name}
                        aria-label={`Name of ${stop.name}`}
                        onchange={(event) =>
                          applyStop(pageIndex, stopIndex, stop, {
                            name: event.currentTarget.value,
                          })}
                      />
                    </label>
                    <label class="field">
                      <span>Unmatched show under</span>
                      <input
                        value={stop.label}
                        placeholder="Other"
                        aria-label={`Heading for ${stop.name}`}
                        onchange={(event) =>
                          applyStop(pageIndex, stopIndex, stop, {
                            label: event.currentTarget.value,
                          })}
                      />
                    </label>
                    <label class="check">
                      <input
                        type="checkbox"
                        checked={stop.showUngrouped}
                        aria-label={`Show unmatched departures of ${stop.name}`}
                        onchange={(event) =>
                          applyStop(pageIndex, stopIndex, stop, {
                            showUngrouped: event.currentTarget.checked,
                          })}
                      />
                      <span>Show what matches no direction</span>
                    </label>
                    <div class="grid">
                      <label class="field">
                        <span>Rows / stop</span>
                        <input
                          type="number"
                          min="0"
                          value={stop.maxDepartures ?? ""}
                          placeholder={String(
                            stopDefaults.maxDeparturesPerStop,
                          )}
                          aria-label={`Rows per stop at ${stop.name}`}
                          onchange={(event) =>
                            applyCount(
                              pageIndex,
                              stopIndex,
                              stop,
                              "maxDepartures",
                              event.currentTarget,
                            )}
                        />
                      </label>
                      <label class="field">
                        <span>Rows / line</span>
                        <input
                          type="number"
                          min="0"
                          value={stop.perLineDepartures ?? ""}
                          placeholder={String(
                            stopDefaults.maxDeparturesPerRoute,
                          )}
                          aria-label={`Rows per line at ${stop.name}`}
                          onchange={(event) =>
                            applyCount(
                              pageIndex,
                              stopIndex,
                              stop,
                              "perLineDepartures",
                              event.currentTarget,
                            )}
                        />
                      </label>
                      <label class="field">
                        <span>Hours ahead</span>
                        <input
                          type="number"
                          min="0"
                          value={stop.hoursInAdvance ?? ""}
                          placeholder="all"
                          aria-label={`Hours ahead at ${stop.name}`}
                          onchange={(event) =>
                            applyCount(
                              pageIndex,
                              stopIndex,
                              stop,
                              "hoursInAdvance",
                              event.currentTarget,
                            )}
                        />
                      </label>
                    </div>

                    {#each stop.directions as heading, headingIndex (headingIndex)}
                      <div class="row sub2">
                        <button
                          class="row-open"
                          data-role="direction"
                          aria-expanded={openHeading === headingIndex}
                          onclick={() => toggleHeading(headingIndex)}
                        >
                          <span class="row-text">
                            <span class="name">{headingTitle(heading)}</span>
                            <span class="meta">{headingSummary(heading)}</span>
                          </span>
                          {@render chevron(openHeading === headingIndex)}
                        </button>
                      </div>

                      {#if openHeading === headingIndex}
                        <div class="children">
                          <label class="field">
                            <span>Name</span>
                            <input
                              value={heading.direction}
                              placeholder="->City"
                              aria-label={`Name of direction ${headingIndex + 1} of ${stop.name}`}
                              onchange={(event) =>
                                renameHeading(
                                  pageIndex,
                                  stopIndex,
                                  stop,
                                  headingIndex,
                                  event.currentTarget.value,
                                )}
                            />
                          </label>

                          <!-- A direction is a filter: every match is kept as
                             text, so "18 Stachus", "18" and "Stachus" all work
                             and stay editable instead of being toggled away. -->
                          <div class="matches" data-role="matches">
                            {#if heading.patterns.length === 0}
                              <p class="note">
                                No match yet - this direction filters nothing.
                              </p>
                            {/if}
                            {#each heading.patterns as pattern, patternIndex (patternIndex)}
                              <div class="match" data-role="match">
                                <input
                                  value={pattern}
                                  aria-label={`Match ${patternIndex + 1} of ${headingTitle(heading)}`}
                                  onchange={(event) =>
                                    setMatch(
                                      pageIndex,
                                      stopIndex,
                                      stop,
                                      headingIndex,
                                      patternIndex,
                                      event.currentTarget.value,
                                    )}
                                />
                                <button
                                  class="icon-button"
                                  aria-label={`Remove the match ${pattern || patternIndex + 1} from ${headingTitle(heading)}`}
                                  onclick={() =>
                                    removeMatch(
                                      pageIndex,
                                      stopIndex,
                                      stop,
                                      headingIndex,
                                      patternIndex,
                                    )}
                                >
                                  ×
                                </button>
                              </div>
                            {/each}
                          </div>

                          <label class="field">
                            <span>Add a match</span>
                            <input
                              placeholder="18 Stachus, 18, or Stachus"
                              aria-label={`Add a match to direction ${headingIndex + 1} of ${stop.name}`}
                              onchange={(event) =>
                                addTypedMatch(
                                  pageIndex,
                                  stopIndex,
                                  stop,
                                  headingIndex,
                                  event.currentTarget,
                                )}
                            />
                          </label>

                          {#if linesLoading.get(stop.stationId)}
                            <p class="note">Loading the stop's lines…</p>
                          {:else if linesProblem.get(stop.stationId)}
                            <p class="problem" role="alert">
                              The lines could not be loaded: {linesProblem.get(
                                stop.stationId,
                              )}
                            </p>
                          {:else if linesByStop.has(stop.stationId)}
                            {#if linesShownFor(stop).length === 0}
                              <p class="note">The departures named no line.</p>
                            {:else}
                              {#if linesShownFor(stop).length > 6}
                                <label class="field">
                                  <span>Filter the lines</span>
                                  <input
                                    value={lineFilter}
                                    placeholder="18, S3, Stachus…"
                                    aria-label={`Filter the lines of ${stop.name}`}
                                    oninput={(event) =>
                                      (lineFilter = event.currentTarget.value)}
                                  />
                                </label>
                              {/if}
                              {#each shownLines(stop) as line (line.line)}
                                <div class="line-row">
                                  <button
                                    class="chip line"
                                    class:is-on={heading.patterns.includes(
                                      line.line,
                                    )}
                                    aria-pressed={heading.patterns.includes(
                                      line.line,
                                    )}
                                    aria-label={`Add every ${line.line} of ${stop.name}`}
                                    onclick={() =>
                                      addMatch(
                                        pageIndex,
                                        stopIndex,
                                        stop,
                                        headingIndex,
                                        linePattern(line.line),
                                      )}
                                  >
                                    {line.line}
                                  </button>
                                  <button
                                    class="chip"
                                    aria-expanded={openLine === line.line}
                                    aria-label={`Show the destinations of ${line.line}`}
                                    onclick={() =>
                                      (openLine =
                                        openLine === line.line
                                          ? null
                                          : line.line)}
                                  >
                                    {line.destinations.length} ▾
                                  </button>
                                  {#if openLine === line.line}
                                    {#each line.destinations as destination (destination)}
                                      <button
                                        class="chip"
                                        class:is-on={heading.patterns.includes(
                                          destinationPattern(
                                            line.line,
                                            destination,
                                          ),
                                        )}
                                        aria-pressed={heading.patterns.includes(
                                          destinationPattern(
                                            line.line,
                                            destination,
                                          ),
                                        )}
                                        aria-label={`Add ${line.line} ${destination}`}
                                        onclick={() =>
                                          addMatch(
                                            pageIndex,
                                            stopIndex,
                                            stop,
                                            headingIndex,
                                            destinationPattern(
                                              line.line,
                                              destination,
                                            ),
                                          )}
                                      >
                                        {destination}
                                      </button>
                                    {/each}
                                  {/if}
                                </div>
                              {/each}
                            {/if}
                          {:else}
                            <button
                              class="button button-secondary"
                              onclick={() => loadLines(stop)}
                            >
                              Load the stop's lines
                            </button>
                          {/if}

                          <button
                            class="button button-secondary delete"
                            onclick={() =>
                              removeHeading(
                                pageIndex,
                                stopIndex,
                                stop,
                                headingIndex,
                              )}
                          >
                            ⨯ Direction
                          </button>
                        </div>
                      {/if}
                    {/each}

                    <button
                      class="row add"
                      data-role="add-direction"
                      onclick={() => addHeading(pageIndex, stopIndex, stop)}
                    >
                      {@render plus()}
                      <span class="name">Direction</span>
                    </button>

                    {#if confirming === `stop:${pageIndex}:${stopIndex}`}
                      <div class="actions">
                        <button
                          class="button button-secondary"
                          onclick={() => (confirming = null)}>Keep</button
                        >
                        <button
                          class="button button-secondary delete"
                          onclick={() => {
                            confirming = null;
                            openStop = null;
                            openHeading = null;
                            onRemoveStop(pageIndex, stopIndex);
                          }}
                        >
                          ⨯ {stop.name}
                        </button>
                      </div>
                    {:else}
                      <div class="actions">
                        <button
                          class="button button-secondary delete"
                          aria-label={`Delete ${stop.name}`}
                          onclick={() =>
                            (confirming = `stop:${pageIndex}:${stopIndex}`)}
                        >
                          ⨯ Stop
                        </button>
                      </div>
                    {/if}
                  </div>
                {/if}
              {/each}

              {#if openForm === "add-stop"}
                <div class="form">
                  <label class="field">
                    <span>Find a stop</span>
                    <input
                      bind:value={stopQuery}
                      placeholder="e.g. Giesing"
                      aria-label="Search a stop to add"
                      onkeydown={(event) => {
                        if (event.key === "Enter") {
                          void searchStops();
                        }
                      }}
                    />
                  </label>
                  <div class="actions">
                    <button
                      class="button button-secondary"
                      onclick={() => toggleForm("add-stop")}>Cancel</button
                    >
                    <button
                      class="button button-primary"
                      disabled={isSearchingStops || stopQuery.trim() === ""}
                      onclick={searchStops}
                    >
                      {isSearchingStops ? "Searching…" : "Search"}
                    </button>
                  </div>
                  {#if stopSearchProblem}
                    <p class="problem" role="alert">{stopSearchProblem}</p>
                  {/if}
                  {#each stopMatches as match (match.stationId)}
                    <button
                      class="row sub"
                      onclick={() => addStop(pageIndex, match)}
                    >
                      <span class="name">{match.stationName}</span>
                      <span class="meta">{match.stationId}</span>
                      {@render plus()}
                    </button>
                  {/each}
                </div>
              {:else}
                <button
                  class="row add"
                  data-role="add-stop"
                  onclick={openStopSearch}
                >
                  {@render plus()}
                  <span class="name">Stop</span>
                </button>
              {/if}

              <div class="actions">
                <button
                  class="button button-secondary"
                  data-role="page-settings"
                  aria-expanded={openForm === "page"}
                  onclick={() => openPageForm(page)}
                >
                  ⚙ Settings
                </button>
                {#if confirming === `page:${pageIndex}`}
                  <button
                    class="button button-secondary"
                    onclick={() => (confirming = null)}>Keep</button
                  >
                  <button
                    class="button button-secondary delete"
                    onclick={() => {
                      confirming = null;
                      openPage = null;
                      onRemovePage(pageIndex);
                    }}
                  >
                    ⨯ “{page.title}”
                  </button>
                {:else}
                  <button
                    class="button button-secondary delete"
                    aria-label={`Delete the route ${page.title}`}
                    onclick={() => (confirming = `page:${pageIndex}`)}
                  >
                    ⨯ Route
                  </button>
                {/if}
              </div>
            </div>
          {/if}
        {/if}
      </li>
    {/each}
  </ul>

  {#if pages.length === 0}
    <p class="note">
      This file has no stops and no routes yet. Add a route, or paste a config
      in the TOML tab.
    </p>
  {/if}
  {#if openForm === "new-page" && newPageDraft}
    <div class="form">
      <label class="field">
        <span>Path</span>
        <input
          bind:value={newPageDraft.path}
          placeholder="/work"
          aria-label="New route path"
        />
      </label>
      <label class="field">
        <span>Title</span>
        <input
          bind:value={newPageDraft.title}
          placeholder="the path, unless you name it"
          aria-label="New route title"
        />
      </label>
      {#if newPageProblem}
        <p class="problem" role="alert">{newPageProblem}</p>
      {/if}
      <div class="actions">
        <button
          class="button button-secondary"
          onclick={() => toggleForm("new-page")}>Cancel</button
        >
        <button
          class="button button-primary"
          disabled={!canCreatePage}
          onclick={applyNewPage}
        >
          Create
        </button>
      </div>
    </div>
  {:else}
    <div class="actions">
      <button
        class="button button-secondary"
        data-role="add-page"
        onclick={openNewPage}>+ Route</button
      >
      <button class="button button-secondary" onclick={onAddStops}
        >Wizard…</button
      >
    </div>
  {/if}

  {#if openForm === "defaults" && defaultsDraft}
    <div class="form">
      <DisplayFields draft={defaultsDraft} />
      <div class="actions">
        <button
          class="button button-secondary"
          onclick={() => toggleForm("defaults")}>Cancel</button
        >
        <button class="button button-primary" onclick={applyDefaults}
          >Apply</button
        >
      </div>
    </div>
  {:else}
    <button
      class="row disclosure"
      data-role="defaults"
      onclick={() => {
        defaultsDraft = draftOfSettings(defaults);
        toggleForm("defaults");
      }}
    >
      <span class="row-text">
        <span class="name">Defaults for every page</span>
        <span class="meta">{settingsSummary(defaults)}</span>
      </span>
      {@render chevron(false)}
    </button>
  {/if}
</div>

<style>
  /* The dialog owns the type and the buttons; the configurator only adds the
     layout of one line per row. Font sizes follow the other screens: 1rem for
     names, 0.875rem for the meta line. */
  .cfg {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    flex: 1 1 auto;
    min-height: 0;
    min-width: 0;
    /* Material's advice for wide screens: keep the line length readable
       instead of stretching a list across a 27 inch display. */
    width: 100%;
    max-width: 44rem;
    margin: 0 auto;
    overflow-y: auto;
    overflow-x: hidden;
    font-size: 0.9375rem;
    color: #111827;
  }

  .rows {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    border-top: 1px solid #e5e7eb;
  }

  .row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    min-height: 3rem;
    padding: 0;
    border: none;
    border-bottom: 1px solid #e5e7eb;
    background: transparent;
    color: #111827;
    font: inherit;
    text-align: left;
    cursor: pointer;
  }

  .row:last-child {
    border-bottom: none;
  }

  /* A row is one tappable line: the label with what it holds underneath, and
     the disclosure chevron at the trailing edge (Material's "label text with
     supporting text" list item). */
  .row-open {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex: 1 1 auto;
    min-width: 0;
    min-height: 3.5rem;
    padding: 0.3rem 0;
    border: none;
    background: transparent;
    color: inherit;
    font: inherit;
    text-align: left;
    cursor: pointer;
    touch-action: manipulation;
  }

  .row-open:active {
    background: #e5e7eb;
  }

  /* A row the file decides, not the finger: no tap, no hover. */
  .row-open.is-static {
    cursor: default;
  }

  .row-open.is-static:active {
    background: transparent;
  }

  :global([data-theme="dark"]) .row-open:active {
    background: #1f2937;
  }

  .row-text {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    flex: 1 1 auto;
    min-width: 0;
  }

  .page-row {
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }

  .page-row.dragging {
    opacity: 0.5;
  }

  .page-row.drop-target {
    outline: 2px solid #087bc4;
    outline-offset: -2px;
  }

  /* The grip is the only part that starts a drag, so a tap still opens the page.
     It is as wide as a thumb, like the chevron. */
  .grip {
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 0 0 2.75rem;
    min-height: 2.75rem;
    color: #6b7280;
    font-size: 1.1rem;
    line-height: 1;
    cursor: grab;
    touch-action: none;
    user-select: none;
  }

  .grip:active {
    cursor: grabbing;
  }

  :global([data-theme="dark"]) .grip {
    color: #9ca3af;
  }

  .row:active {
    background: #e5e7eb;
  }

  .row .name {
    flex: 1 1 auto;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-weight: 500;
  }

  .row .meta {
    color: #6b7280;
    font-size: 0.8125rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* The second line is supporting text, not a second column: it never wraps
     and never pushes the label aside. */
  .row-text .name,
  .row-text .meta {
    display: block;
    flex: 0 1 auto;
  }

  /* The row's icon. It is drawn by a snippet, so it has no scope class: only a
     rule anchored at .cfg reaches it. The closed chevron turns a quarter turn
     to say "open". */
  .cfg :global(.chevron) {
    flex: 0 0 auto;
    color: #087bc4;
    transition: transform 120ms ease;
  }

  .cfg :global(.chevron-open) {
    transform: rotate(90deg);
  }

  .row.sub .row-text .name {
    font-size: 0.9375rem;
  }

  .row.sub2 .row-text .name {
    font-size: 0.875rem;
  }

  .row.add .name {
    color: #087bc4;
  }

  .children {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    padding: 0.5rem 0;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    min-width: 0;
    font-size: 0.875rem;
    color: #4b5563;
  }

  .field input,
  .match input {
    width: 100%;
    min-width: 0;
    min-height: 2.75rem;
    padding: 0.4rem 0.5rem;
    border: 1px solid #d1d5db;
    border-radius: 0.375rem;
    background: #ffffff;
    color: #111827;
    font: inherit;
    font-size: 1rem;
  }

  .check {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    min-height: 2.75rem;
    font-size: 1rem;
    color: #111827;
  }

  .check input {
    flex: 0 0 auto;
    width: 1.25rem;
    height: 1.25rem;
    accent-color: #087bc4;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(5rem, 1fr));
    gap: 0.5rem;
  }

  .form {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    padding: 0.5rem;
    border: 1px solid #e5e7eb;
    border-radius: 0.5rem;
    background: #f9fafb;
  }

  .note,
  .problem {
    margin: 0;
    font-size: 0.875rem;
  }

  .note {
    color: #4b5563;
  }

  .problem {
    color: #b91c1c;
  }

  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .actions :global(.button) {
    min-height: 2.75rem;
  }

  .delete {
    border: 1px solid #b91c1c;
    background: transparent;
    color: #b91c1c;
    font-weight: 500;
  }

  :global([data-theme="dark"]) .delete {
    border-color: #fca5a5;
    color: #fca5a5;
  }

  .matches {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .icon-button {
    flex: 0 0 auto;
    min-width: 2.75rem;
    min-height: 2.75rem;
    border: 1px solid #d1d5db;
    border-radius: 0.375rem;
    background: #ffffff;
    color: #111827;
    font: inherit;
    font-size: 1rem;
    cursor: pointer;
  }

  .line-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.35rem;
  }

  .chip {
    min-height: 2.5rem;
    max-width: 100%;
    padding: 0.25rem 0.75rem;
    border: 1px solid #d1d5db;
    border-radius: 0.375rem;
    background: #ffffff;
    color: #111827;
    font: inherit;
    font-size: 0.875rem;
    cursor: pointer;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .chip.line {
    min-width: 2.5rem;
    font-weight: 600;
  }

  /* A match the direction already holds: filled, and tapping it adds nothing. */
  .chip.is-on {
    background: #087bc4;
    border-color: #087bc4;
    color: #ffffff;
  }

  .match {
    display: flex;
    align-items: center;
    gap: 0.35rem;
  }

  .row:focus-visible,
  .chip:focus-visible,
  .icon-button:focus-visible {
    outline: 2px solid #087bc4;
    outline-offset: 2px;
  }

  /* Dark theme, the same shapes and the dialog's colours. */
  :global([data-theme="dark"]) .cfg,
  :global([data-theme="dark"]) .row,
  :global([data-theme="dark"]) .check {
    color: #f9fafb;
  }

  :global([data-theme="dark"]) .rows,
  :global([data-theme="dark"]) .form {
    background: #111827;
    border-color: #374151;
  }

  :global([data-theme="dark"]) .row {
    border-bottom-color: #374151;
  }

  :global([data-theme="dark"]) .row:active {
    background: #374151;
  }

  :global([data-theme="dark"]) .row .meta,
  :global([data-theme="dark"]) .note,
  :global([data-theme="dark"]) .field {
    color: #d1d5db;
  }

  :global([data-theme="dark"]) .cfg :global(.chevron),
  :global([data-theme="dark"]) .row.add .name {
    color: #93c5fd;
  }

  :global([data-theme="dark"]) .row .meta {
    color: #9ca3af;
  }

  :global([data-theme="dark"]) .field input,
  :global([data-theme="dark"]) .match input,
  :global([data-theme="dark"]) .chip,
  :global([data-theme="dark"]) .icon-button {
    background: #1f2937;
    border-color: #4b5563;
    color: #f9fafb;
  }

  :global([data-theme="dark"]) .chip.is-on {
    background: #087bc4;
    border-color: #087bc4;
    color: #ffffff;
  }

  :global([data-theme="dark"]) .problem {
    color: #fca5a5;
  }
</style>
