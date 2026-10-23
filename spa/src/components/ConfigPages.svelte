<script lang="ts">
  import DisplayFields from "./DisplayFields.svelte";
  import {
    draftOfSettings,
    settingsOfDraft,
    type ConfigPage,
    type ConfigPageEdit,
    type DisplayDraft,
    type DisplaySettings,
    type NewConfigPage,
  } from "../utils/config-pages.js";

  let {
    pages,
    defaults,
    onReorder,
    onRemovePage,
    onRemoveStop,
    onApplyPage,
    onApplyPageDisplay,
    onApplyDefaults,
    onAddPage,
    onAddStops,
  }: {
    pages: ConfigPage[];
    /** The file's own display settings, which every page inherits. */
    defaults: DisplaySettings;
    onReorder: (from: number, to: number) => void;
    onRemovePage: (index: number) => void;
    onRemoveStop: (pageIndex: number, stopIndex: number) => void;
    onApplyPage: (index: number, edit: ConfigPageEdit) => void;
    onApplyPageDisplay: (index: number, values: DisplaySettings) => void;
    onApplyDefaults: (values: DisplaySettings) => void;
    onAddPage: (page: NewConfigPage) => void;
    onAddStops: () => void;
  } = $props();

  /** The page whose deletion is being confirmed, if any. */
  let confirmingPage = $state<number | null>(null);
  /** "pageIndex:stopIndex" of the stop whose deletion is being confirmed. */
  let confirmingStop = $state<string | null>(null);
  let draggedPage = $state<number | null>(null);
  /** The page being edited, and its unsaved form. */
  let editingPage = $state<number | null>(null);
  let draft = $state<Draft | null>(null);
  /** The open defaults form, if any. */
  let defaultsDraft = $state<DisplayDraft | null>(null);

  /** A stop's matches are edited as one pattern per line. */
  type Draft = {
    path: string;
    title: string;
    settings: DisplayDraft;
    stops: {
      label: string;
      showUngrouped: boolean;
      directions: { direction: string; patterns: string }[];
    }[];
  };

  function stopKey(pageIndex: number, stopIndex: number): string {
    return `${pageIndex}:${stopIndex}`;
  }

  function dropOn(index: number) {
    if (draggedPage !== null && draggedPage !== index) {
      onReorder(draggedPage, index);
    }
    draggedPage = null;
  }

  function startEditing(index: number, page: ConfigPage) {
    confirmingPage = null;
    confirmingStop = null;
    editingPage = index;
    draft = {
      path: page.path,
      title: page.title,
      settings: draftOfSettings(page.display),
      stops: page.stops.map((stop) => ({
        label: stop.label,
        showUngrouped: stop.showUngrouped,
        directions: stop.directions.map((direction) => ({
          direction: direction.direction,
          patterns: direction.patterns.join("\n"),
        })),
      })),
    };
  }

  function addDirection(stop: Draft["stops"][number]) {
    stop.directions = [...stop.directions, { direction: "", patterns: "" }];
  }

  function removeDirection(
    stop: Draft["stops"][number],
    directionIndex: number,
  ) {
    stop.directions = stop.directions.filter((_, at) => at !== directionIndex);
  }

  function patternsOf(text: string): string[] {
    return text
      .split("\n")
      .map((pattern) => pattern.trim())
      .filter((pattern) => pattern !== "");
  }

  function stopEditing() {
    editingPage = null;
    draft = null;
  }

  /** Why the draft cannot be applied, or "" while it can. */
  const pathProblem = $derived.by(() => {
    if (draft === null) {
      return "";
    }
    const path = draft.path.trim();
    if (!path.startsWith("/")) {
      return "A path starts with a slash, like /work.";
    }
    const taken = pages.some(
      (page, at) => at !== editingPage && page.path === path,
    );
    return taken ? "Another page already uses this path." : "";
  });

  function applyDraft() {
    if (editingPage === null || draft === null || pathProblem !== "") {
      return;
    }
    const index = editingPage;
    const edit: ConfigPageEdit = {
      path: draft.path.trim(),
      title: draft.title,
      stops: draft.stops.map((stop) => ({
        label: stop.label,
        showUngrouped: stop.showUngrouped,
        directions: stop.directions.map((direction) => ({
          direction: direction.direction,
          patterns: patternsOf(direction.patterns),
        })),
      })),
    };
    const settings = settingsOfDraft(draft.settings);
    stopEditing();
    onApplyPage(index, edit);
    onApplyPageDisplay(index, settings);
  }

  function openDefaults() {
    defaultsDraft = draftOfSettings(defaults);
  }

  function applyDefaults() {
    if (defaultsDraft === null) {
      return;
    }
    const values = settingsOfDraft(defaultsDraft);
    defaultsDraft = null;
    onApplyDefaults(values);
  }

  /** The new page's form, if it is open. */
  let newPageDraft = $state<{ path: string; title: string } | null>(null);

  /** Why the new page cannot be created yet, or "" while it can. */
  const newPageProblem = $derived.by(() => {
    if (newPageDraft === null) {
      return "";
    }
    const path = newPageDraft.path.trim();
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
    stopEditing();
    newPageDraft = { path: "", title: "" };
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
    onAddPage(page);
  }

  /** What the defaults card says at a glance. */
  const defaultsSummary = $derived.by(() => {
    const count = Object.keys(defaults).length;
    if (count === 0) {
      return "Nothing set here: the app's own defaults apply.";
    }
    return `${count} setting${count === 1 ? "" : "s"} set here, inherited by every page.`;
  });
</script>

<div class="pages">
  <section class="defaults-card" aria-label="Defaults for every page">
    <header class="page-head">
      <div class="page-title">
        <strong>Defaults for every page</strong>
        <span class="page-path">{defaultsSummary}</span>
      </div>
      {#if defaultsDraft === null}
        <button class="button button-secondary" onclick={openDefaults}>
          Edit defaults
        </button>
      {/if}
    </header>
    {#if defaultsDraft !== null}
      <div class="page-form">
        <DisplayFields draft={defaultsDraft} />
        <div class="page-form-actions">
          <button class="button button-secondary" onclick={() => (defaultsDraft = null)}>
            Cancel
          </button>
          <button class="button button-primary" onclick={applyDefaults}>
            Apply defaults
          </button>
        </div>
      </div>
    {/if}
  </section>

  {#each pages as page, index (index)}
    <article
      class="page-card"
      class:is-dragged={draggedPage === index}
      draggable={editingPage !== index}
      data-page-path={page.path}
      ondragstart={() => (draggedPage = index)}
      ondragover={(event) => event.preventDefault()}
      ondrop={() => dropOn(index)}
      ondragend={() => (draggedPage = null)}
    >
      <header class="page-head">
        <span class="drag-handle" aria-hidden="true">⠿</span>
        <div class="page-title">
          <strong>{page.title}</strong>
          {#if page.path !== page.title}
            <span class="page-path">{page.path}</span>
          {/if}
        </div>
        <div class="page-actions">
          <button
            class="icon-button"
            aria-label={`Move ${page.title} up`}
            disabled={index === 0}
            onclick={() => onReorder(index, index - 1)}
          >
            ↑
          </button>
          <button
            class="icon-button"
            aria-label={`Move ${page.title} down`}
            disabled={index === pages.length - 1}
            onclick={() => onReorder(index, index + 1)}
          >
            ↓
          </button>
          <button
            class="button button-secondary"
            onclick={() => startEditing(index, page)}
          >
            Edit
          </button>
          <button
            class="button button-secondary"
            onclick={() => (confirmingPage = index)}
          >
            Delete page
          </button>
        </div>
      </header>

      {#if editingPage === index && draft}
        <div class="page-form">
          <label class="page-form-field">
            <span>Title</span>
            <input bind:value={draft.title} placeholder={page.path} />
          </label>
          <label class="page-form-field">
            <span>Path</span>
            <input bind:value={draft.path} aria-invalid={pathProblem !== ""} />
          </label>
          {#if pathProblem}
            <p class="page-form-problem" role="alert">{pathProblem}</p>
          {/if}

          <fieldset class="page-form-stops">
            <legend>Stops</legend>
            {#each draft.stops as stop, stopIndex (page.stops[stopIndex].stationId)}
              <div class="page-form-stop">
                <span class="page-form-stop-name">{page.stops[stopIndex].name}</span>
                <label class="page-form-field">
                  <span>Heading for everything else</span>
                  <input
                    bind:value={stop.label}
                    placeholder="Other"
                    aria-label={`Heading for ${page.stops[stopIndex].name}`}
                  />
                </label>
                <label class="page-form-check">
                  <input
                    type="checkbox"
                    bind:checked={stop.showUngrouped}
                    aria-label={`Show unmatched departures of ${page.stops[stopIndex].name}`}
                  />
                  <span>Show the departures that match no heading</span>
                </label>

                <div class="page-form-directions">
                  <p class="page-form-hint">
                    Headings: one match per line, matched against the line and the
                    destination.
                  </p>
                  {#each stop.directions as direction, directionIndex (directionIndex)}
                    <div class="page-form-direction">
                      <input
                        class="page-form-direction-name"
                        placeholder="->City"
                        aria-label={`Heading ${directionIndex + 1} of ${page.stops[stopIndex].name}`}
                        bind:value={direction.direction}
                      />
                      <textarea
                        rows="2"
                        placeholder="U2 Messestadt"
                        aria-label={`Matches for heading ${directionIndex + 1} of ${page.stops[stopIndex].name}`}
                        bind:value={direction.patterns}
                      ></textarea>
                      <button
                        class="icon-button"
                        aria-label={`Remove heading ${directionIndex + 1} of ${page.stops[stopIndex].name}`}
                        onclick={() => removeDirection(stop, directionIndex)}
                      >
                        ×
                      </button>
                    </div>
                  {/each}
                  <button
                    class="button button-secondary page-form-add-heading"
                    onclick={() => addDirection(stop)}
                  >
                    Add heading
                  </button>
                </div>
              </div>
            {/each}
          </fieldset>

          <fieldset class="page-form-stops">
            <legend>This page's own settings</legend>
            <p class="page-form-hint">
              A field left empty uses the defaults above.
            </p>
            <DisplayFields draft={draft.settings} />
          </fieldset>

          <div class="page-form-actions">
            <button class="button button-secondary" onclick={stopEditing}>Cancel</button>
            <button
              class="button button-primary"
              disabled={pathProblem !== ""}
              onclick={applyDraft}
            >
              Apply changes
            </button>
          </div>
        </div>
      {:else}
        <ul class="page-stops">
          {#each page.stops as stop, stopIndex (stop.stationId)}
            <li class="page-stop">
              <span class="page-stop-name">{stop.name}</span>
              {#if stop.label}
                <span class="page-stop-label">{stop.label}</span>
              {/if}
              {#if stop.directions.length > 0}
                <span class="page-stop-label">
                  {stop.directions.length} heading{stop.directions.length === 1 ? "" : "s"}
                </span>
              {/if}
              {#if confirmingStop === stopKey(index, stopIndex)}
                <span class="page-stop-confirm">
                  <button class="button button-secondary" onclick={() => (confirmingStop = null)}>
                    Keep
                  </button>
                  <button
                    class="button button-danger"
                    onclick={() => {
                      confirmingStop = null;
                      onRemoveStop(index, stopIndex);
                    }}
                  >
                    Delete
                  </button>
                </span>
              {:else}
                <button
                  class="icon-button"
                  aria-label={`Delete ${stop.name}`}
                  onclick={() => (confirmingStop = stopKey(index, stopIndex))}
                >
                  ×
                </button>
              {/if}
            </li>
          {/each}
        </ul>
      {/if}

      {#if confirmingPage === index}
        <div class="page-confirm" role="status">
          <span>Delete the page “{page.title}”? Its stops go with it.</span>
          <button class="button button-secondary" onclick={() => (confirmingPage = null)}>
            Keep page
          </button>
          <button
            class="button button-danger"
            onclick={() => {
              confirmingPage = null;
              onRemovePage(index);
            }}
          >
            Yes, delete
          </button>
        </div>
      {/if}
    </article>
  {/each}

  {#if pages.length === 0}
    <p class="pages-empty">
      No pages yet. A config written for the server version has its stops outside the
      pages - switch to TOML and press Clean up to convert it.
    </p>
  {/if}

  {#if newPageDraft === null}
    <div class="pages-actions">
      <button class="button button-secondary" onclick={openNewPage}>
        New page
      </button>
      <button class="button button-secondary add-stops" onclick={onAddStops}>
        Add stops…
      </button>
    </div>
  {:else}
    <div class="new-page-form">
      <label class="page-form-field">
        <span>Path</span>
        <input
          bind:value={newPageDraft.path}
          placeholder="/work"
          aria-label="New page path"
        />
      </label>
      <label class="page-form-field">
        <span>Title</span>
        <input
          bind:value={newPageDraft.title}
          placeholder="The path, unless you name it"
          aria-label="New page title"
        />
      </label>
      {#if newPageProblem}
        <p class="page-form-problem" role="alert">{newPageProblem}</p>
      {/if}
      <div class="page-form-actions">
        <button class="button button-secondary" onclick={() => (newPageDraft = null)}>
          Cancel
        </button>
        <button class="button button-primary" disabled={!canCreatePage} onclick={applyNewPage}>
          Create page
        </button>
      </div>
    </div>
  {/if}
</div>

<style>
  .pages {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    overflow-y: auto;
    overflow-x: hidden;
    flex: 1 1 auto;
    min-height: 0;
    min-width: 0;
    padding-right: 0.25rem;
  }

  .page-card {
    border: 1px solid #e5e7eb;
    border-radius: 0.5rem;
    padding: 0.5rem 0.75rem;
    background: #f9fafb;
  }

  .defaults-card {
    border: 1px solid #dbeafe;
    border-radius: 0.5rem;
    padding: 0.5rem 0.75rem;
    background: #eff6ff;
  }

  :global([data-theme="dark"]) .defaults-card {
    border-color: #1e40af;
    background: #1e293b;
  }

  :global([data-theme="dark"]) .page-card {
    border-color: #4b5563;
    background: #1f2937;
  }

  .page-card.is-dragged {
    opacity: 0.5;
  }

  .page-head {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .drag-handle {
    cursor: grab;
    color: #9ca3af;
    font-size: 1.1rem;
  }

  .page-title {
    display: flex;
    flex-direction: column;
    flex: 1 1 8rem;
    min-width: 0;
  }

  .page-path {
    font-size: 0.75rem;
    color: #6b7280;
    font-family: monospace;
  }

  :global([data-theme="dark"]) .page-path {
    color: #9ca3af;
  }

  .page-actions {
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }

  .page-stops {
    list-style: none;
    margin: 0.5rem 0 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .page-stop {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
  }

  .page-stop-name {
    flex: 1 1 auto;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .page-stop-label {
    font-size: 0.75rem;
    color: #6b7280;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 8rem;
  }

  :global([data-theme="dark"]) .page-stop-label {
    color: #9ca3af;
  }

  .page-form {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-top: 0.5rem;
    padding-top: 0.5rem;
    border-top: 1px solid #e5e7eb;
    min-width: 0;
  }

  :global([data-theme="dark"]) .page-form {
    border-top-color: #4b5563;
  }

  .page-form-field {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    font-size: 0.8rem;
    flex: 1 1 8rem;
    min-width: 0;
  }

  .page-form-field input {
    padding: 0.35rem 0.5rem;
    border: 1px solid #d1d5db;
    border-radius: 0.375rem;
    font-size: 0.85rem;
    width: 100%;
    box-sizing: border-box;
  }

  :global([data-theme="dark"]) .page-form-field input {
    background: #111827;
    border-color: #4b5563;
    color: #e5e7eb;
  }

  .page-form-problem {
    margin: 0;
    font-size: 0.8rem;
    color: #b91c1c;
  }

  :global([data-theme="dark"]) .page-form-problem {
    color: #fca5a5;
  }

  .page-form-stops {
    border: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    /* A fieldset defaults to its content's min-content width, which overflows. */
    min-inline-size: 0;
  }

  .page-form-stops legend {
    font-size: 0.8rem;
    font-weight: 600;
    padding: 0;
  }

  .page-form-stop {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    gap: 0.5rem;
  }

  .page-form-stop-name {
    flex: 1 1 6rem;
    font-size: 0.85rem;
    font-weight: 500;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .page-form-check {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.8rem;
    flex: 1 1 12rem;
  }

  .page-form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
  }

  .page-form-directions {
    flex: 1 1 100%;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    padding-left: 0.75rem;
    border-left: 2px solid #e5e7eb;
  }

  :global([data-theme="dark"]) .page-form-directions {
    border-left-color: #4b5563;
  }

  .page-form-hint {
    margin: 0;
    font-size: 0.75rem;
    color: #6b7280;
  }

  :global([data-theme="dark"]) .page-form-hint {
    color: #9ca3af;
  }

  .page-form-direction {
    display: flex;
    align-items: flex-start;
    gap: 0.35rem;
    flex-wrap: wrap;
    min-width: 0;
  }

  .page-form-direction input,
  .page-form-direction textarea {
    padding: 0.3rem 0.45rem;
    border: 1px solid #d1d5db;
    border-radius: 0.375rem;
    font-size: 0.8rem;
    box-sizing: border-box;
  }

  .page-form-direction input {
    flex: 1 1 7rem;
    min-width: 5rem;
  }

  .page-form-direction textarea {
    flex: 1 1 auto;
    min-width: 0;
    resize: vertical;
    font-family: inherit;
  }

  :global([data-theme="dark"]) .page-form-direction input,
  :global([data-theme="dark"]) .page-form-direction textarea {
    background: #111827;
    border-color: #4b5563;
    color: #e5e7eb;
  }

  .page-form-add-heading {
    align-self: flex-start;
  }

  .page-stop-confirm {
    display: flex;
    gap: 0.25rem;
  }

  .page-confirm {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 0.5rem;
    padding: 0.5rem;
    border-radius: 0.375rem;
    background: #fef2f2;
    font-size: 0.875rem;
  }

  :global([data-theme="dark"]) .page-confirm {
    background: #7f1d1d;
  }

  .pages-empty {
    color: #6b7280;
    font-size: 0.875rem;
  }

  .add-stops {
    align-self: flex-start;
  }

  .pages-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    align-self: flex-start;
  }

  .new-page-form {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    border: 1px solid #e5e7eb;
    border-radius: 0.5rem;
    padding: 0.5rem 0.75rem;
    background: #f9fafb;
    min-width: 0;
  }

  :global([data-theme="dark"]) .new-page-form {
    border-color: #4b5563;
    background: #1f2937;
  }

  .icon-button {
    min-width: 1.75rem;
    padding: 0.125rem 0.375rem;
  }

  .button-danger {
    background-color: #dc2626;
    color: white;
  }
</style>
