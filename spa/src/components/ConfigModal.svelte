<script lang="ts">
  /* eslint-disable svelte/prefer-svelte-reactivity */
  /* global HTMLInputElement, URL */
  import { tick } from "svelte";
  import { LocalStorageConfigStorage } from "../adapters/storage/local-storage-config-storage.js";
  import { ConfigParser } from "../adapters/config/config-parser.js";
  import ConfigWizard from "./ConfigWizard.svelte";
  import ConfigPages from "./ConfigPages.svelte";
  import {
    moveConfigPage,
    readConfigPages,
    readDisplaySettings,
    removeConfigPage,
    removeConfigStop,
    updateConfigPage,
    addConfigPage,
    updateDisplaySettings,
    type ConfigPageEdit,
    type DisplaySettings,
    type NewConfigPage,
  } from "../utils/config-pages.js";
  import {
    applyWizardConfig,
    getWizardConfigContext,
    type WizardConfigContext,
    type WizardResult,
  } from "../utils/config-modifier.js";
  import {
    cleanUpConfigToml,
    describeCleanup,
  } from "../utils/config-cleanup.js";
  import {
    addOnTheRunSection,
    draftOfOnTheRun,
    hasOnTheRun,
    ON_THE_RUN_FIELDS,
    readOnTheRunSettings,
    settingsOfOnTheRunDraft,
    updateOnTheRunSettings,
    type OnTheRunDraft,
  } from "../utils/on-the-run-section.js";
  import { fetchToml, rawConfigUrl } from "../utils/config-url.js";

  let {
    onSave,
    onCancel,
  }: {
    onSave: (config: string) => Promise<void>;
    onCancel: () => void;
  } = $props();

  let configText = $state("");
  let view = $state<"pages" | "toml">("pages");
  let errorMessage = $state<string | null>(null);
  let notice = $state<string | null>(null);
  /** The text the notice belongs to; any edit makes it stale. */
  let noticeFor = $state("");
  /** A prepared clean-up the user has not applied yet. */
  let pendingCleanup = $state<{
    /** The text it was computed from; an edit elsewhere drops the proposal. */
    for: string;
    toml: string;
    description: string;
  } | null>(null);
  let isSaving = $state(false);
  /** The text as it was loaded; anything else is an unsaved edit. */
  let savedText = $state("");
  /** Set when leaving would throw edits away. */
  let confirmCancel = $state(false);
  let isLoadingExample = $state(false);
  let copySuccess = $state(false);
  let pasteSuccess = $state(false);
  let pasteError = $state(false);
  let showWizard = $state(false);
  let showFullscreenEditor = $state(false);
  let showTweakOverlay = $state(false);
  type TweakEntry = { key: string; value: string; lineIndex: number };
  type TweakSection = { heading: string; entries: TweakEntry[] };
  let tweakSections = $state<TweakSection[]>([]);
  let wizardContext = $state<WizardConfigContext | null>(null);
  const configStorage = new LocalStorageConfigStorage();
  const configParser = new ConfigParser();

  function getCurrentRoutePath(): string {
    const hash = window.location.hash.slice(1); // Remove leading #
    if (!hash || hash === "/") {
      return "/";
    }
    return hash;
  }

  function isOnTheRunRoute(path: string): boolean {
    return path === "on-the-run" || path === "/on-the-run";
  }

  function openWizard() {
    wizardContext = getWizardConfigContext(configText);
    showWizard = true;
  }

  /** True if the line is a TOML section header (not a comment; starts with [ and ends with ]). */
  function isSectionHeader(line: string): boolean {
    const t = line.trim();
    return t.length > 0 && !t.startsWith("#") && t.startsWith("[") && t.endsWith("]");
  }

  /** Section heading text for display (trimmed, trailing # comment removed). */
  function sectionHeadingText(line: string): string {
    return line.trim().replace(/\s*#.*$/, "").trim();
  }

  /** Parse all TOML sections: every non-comment line starting with [ is a heading; collect key=value lines until the next heading. */
  function parseDisplaySections(tomlText: string): TweakSection[] {
    const lines = tomlText.split("\n");
    const sections: TweakSection[] = [];
    let i = 0;
    const keyValueRe = /^\s*([a-z][a-z0-9_]*)\s*=\s*(.*)$/;

    while (i < lines.length) {
      const line = lines[i];
      if (isSectionHeader(line)) {
        const heading = sectionHeadingText(line);
        const entries: TweakEntry[] = [];
        i += 1;
        while (i < lines.length) {
          const next = lines[i];
          if (isSectionHeader(next)) {
            break;
          }
          const kv = next.match(keyValueRe);
          if (kv) {
            const [, key, raw] = kv;
            const rawTrimmed = raw.trim();
            const isNonScalar = rawTrimmed.startsWith("[") || rawTrimmed.startsWith("{");
            if (!isNonScalar) {
              let value = rawTrimmed;
              if (value.startsWith('"')) {
                let end = 1;
                while (end < value.length) {
                  if (value[end] === "\\" && end + 1 < value.length) {
                    end += 2;
                    continue;
                  }
                  if (value[end] === '"') {
                    value = value.slice(1, end).replace(/\\"/g, '"');
                    break;
                  }
                  end += 1;
                }
              } else if (value.startsWith("'") && value.endsWith("'") && value.length >= 2) {
                value = value.slice(1, -1);
              } else {
                const hashIdx = value.indexOf("#");
                if (hashIdx !== -1) value = value.slice(0, hashIdx).trim();
              }
              entries.push({ key, value, lineIndex: i });
            }
          }
          i += 1;
        }
        sections.push({ heading, entries });
        continue;
      }
      i += 1;
    }
    return sections;
  }

  /** Format value for TOML: quote strings, leave numbers/booleans/arrays/inline tables as-is. */
  function tomlValue(value: string): string {
    const trimmed = value.trim();
    if (trimmed === "true" || trimmed === "false") return trimmed;
    const n = Number(trimmed);
    if (!Number.isNaN(n) && trimmed !== "") return trimmed;
    if (trimmed.startsWith("[") || trimmed.startsWith("{")) return trimmed;
    return `"${trimmed.replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"`;
  }

  /** Apply modified tweak sections back to TOML text (updates config text only, does not save). */
  function applyTweakDisplay(tomlText: string, sections: TweakSection[]): string {
    const lines = tomlText.split("\n");
    const lineUpdates = new Map<number, string>();
    for (const section of sections) {
      for (const entry of section.entries) {
        const line = lines[entry.lineIndex];
        if (!line) continue;
        const keyValueRe = /^\s*([a-z][a-z0-9_]*)\s*=\s*(.*)$/;
        if (keyValueRe.test(line)) {
          lineUpdates.set(entry.lineIndex, `${entry.key} = ${tomlValue(entry.value)}`);
        }
      }
    }
    const out: string[] = [];
    for (let idx = 0; idx < lines.length; idx++) {
      out.push(lineUpdates.has(idx) ? lineUpdates.get(idx)! : lines[idx]);
    }
    return out.join("\n");
  }

  function openTweak() {
    tweakSections = parseDisplaySections(configText);
    showTweakOverlay = true;
  }

  function closeTweakAndApply() {
    configText = applyTweakDisplay(configText, tweakSections);
    showTweakOverlay = false;
  }

  let tweakFilterQuery = $state("");
  let tweakFilterInputEl: HTMLInputElement | undefined = $state(undefined);

  $effect(() => {
    if (!showTweakOverlay) return;
    tick().then(() => tweakFilterInputEl?.focus());
  });

  let lastTweakValueFocusedEl: HTMLInputElement | undefined = $state(undefined);

  /** Identity of the value input that has focus (for keeping it visible while editing). */
  const lastTweakFocusedEntry = $derived.by(() => {
    const el = lastTweakValueFocusedEl;
    if (!el?.id?.startsWith?.("tweak-input-")) return undefined;
    const match = el.id.match(/^tweak-input-(\d+)-(\d+)$/);
    if (!match) return undefined;
    return {
      sectionIdx: parseInt(match[1], 10),
      lineIndex: parseInt(match[2], 10),
    };
  });

  function clearTweakFilter() {
    tweakFilterQuery = "";
    tick().then(() => {
      if (
        lastTweakValueFocusedEl &&
        document.contains(lastTweakValueFocusedEl)
      ) {
        lastTweakValueFocusedEl.focus();
        lastTweakValueFocusedEl.scrollIntoView({
          behavior: "smooth",
          block: "nearest",
        });
      } else {
        tweakFilterInputEl?.focus();
      }
    });
  }

  /** Non-empty filter terms (lowercased) for AND matching. */
  const tweakFilterParts = $derived(
    tweakFilterQuery
      .trim()
      .split(/\s+/)
      .filter(Boolean)
      .map((p) => p.toLowerCase()),
  );

  function tweakEntryMatchesFilter(
    entry: TweakEntry,
    parts: string[],
  ): boolean {
    if (parts.length === 0) return true;
    const line = `${entry.key} ${entry.value}`.toLowerCase();
    return parts.every((part) => line.includes(part));
  }

  /** True if the section heading (e.g. on_the_run) matches all filter parts. */
  function tweakSectionHeadingMatchesFilter(
    section: TweakSection,
    parts: string[],
  ): boolean {
    if (parts.length === 0) return true;
    const heading = section.heading.toLowerCase();
    return parts.every((part) => heading.includes(part));
  }

  function tweakSectionHasVisibleEntries(
    section: TweakSection,
    parts: string[],
    sectionIdx: number,
  ): boolean {
    const focused = lastTweakFocusedEntry;
    if (focused?.sectionIdx === sectionIdx) {
      const hasFocusedEntry = section.entries.some(
        (e) => e.lineIndex === focused.lineIndex,
      );
      if (hasFocusedEntry) return true;
    }
    return (
      tweakSectionHeadingMatchesFilter(section, parts) ||
      section.entries.some((e) => tweakEntryMatchesFilter(e, parts))
    );
  }

  /** Show entry if section heading matches (show whole section) or this entry's key/value matches.
   * Always show the entry whose value input is focused, so editing (e.g. clearing) doesn't hide it. */
  function tweakShowEntry(
    section: TweakSection,
    entry: TweakEntry,
    parts: string[],
    sectionIdx: number,
  ): boolean {
    const focused = lastTweakFocusedEntry;
    if (
      focused &&
      focused.sectionIdx === sectionIdx &&
      focused.lineIndex === entry.lineIndex
    ) {
      return true;
    }
    return (
      tweakSectionHeadingMatchesFilter(section, parts) ||
      tweakEntryMatchesFilter(entry, parts)
    );
  }

  /** Keys that appear in more than one section (for disambiguation in labels). */
  const tweakDuplicateKeys = $derived.by(() => {
    const keyCount = new Map<string, number>();
    for (const section of tweakSections) {
      for (const entry of section.entries) {
        keyCount.set(entry.key, (keyCount.get(entry.key) ?? 0) + 1);
      }
    }
    return new Set(
      [...keyCount.entries()].filter(([, n]) => n > 1).map(([k]) => k),
    );
  });

  async function loadStoredConfig(): Promise<void> {
    const storedToml = await configStorage.getConfigToml();
    configText = storedToml || "";
    savedText = configText;
    errorMessage = null; // Clear error when loading
    notice = null;
  }

  // Load raw TOML from storage when modal opens
  $effect(() => {
    void loadStoredConfig();
  });

  // Clear error when text changes
  $effect(() => {
    if (configText && errorMessage) {
      errorMessage = null;
    }
    if (notice && configText !== noticeFor) {
      notice = null;
    }
    // Editing the text makes a prepared clean-up stale.
    if (pendingCleanup && pendingCleanup.for !== configText) {
      pendingCleanup = null;
    }
  });

  /** Says what just happened to the text; the change itself is not saved yet. */
  function showNotice(message: string) {
    notice = message;
    noticeFor = configText;
  }

  /**
   * Rewrites the config into the SPA's shape - but only as a proposal: the
   * rewrite lands in the editor when the user applies it, and Cancel leaves the
   * text exactly as it was. Nothing is saved either way until Save.
   */
  function previewCleanup() {
    notice = null;
    try {
      const cleanup = cleanUpConfigToml(configText);
      if (!cleanup.changed) {
        showNotice(describeCleanup(cleanup));
        return;
      }
      configParser.parseToml(cleanup.toml);
      pendingCleanup = {
        for: configText,
        toml: cleanup.toml,
        description: describeCleanup(cleanup),
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      errorMessage = `Could not clean up the configuration: ${message}`;
    }
  }

  function applyCleanup() {
    if (!pendingCleanup) {
      return;
    }
    const { toml, description } = pendingCleanup;
    pendingCleanup = null;
    configText = toml;
    errorMessage = null;
    showNotice(description);
  }

  function cancelCleanup() {
    pendingCleanup = null;
  }

  const hasOnTheRunPage = $derived(hasOnTheRun(configText));

  /** The Next to me page's own settings, and its open form. */
  const onTheRunSettings = $derived(readOnTheRunSettings(configText));
  let onTheRunDraft = $state<OnTheRunDraft | null>(null);

  function openOnTheRunForm() {
    onTheRunDraft = draftOfOnTheRun(onTheRunSettings);
  }

  function applyOnTheRun() {
    if (onTheRunDraft === null) {
      return;
    }
    const values = settingsOfOnTheRunDraft(onTheRunDraft);
    const before = configText;
    onTheRunDraft = null;
    configText = updateOnTheRunSettings(configText, values);
    if (configText !== before) {
      showNotice("Next to me updated. Save to keep the change.");
    }
  }

  /** The pages the config describes, in file order. */
  const configPages = $derived(readConfigPages(configText));

  /** The settings every page inherits. */
  const globalDisplay = $derived(readDisplaySettings(configText, "global"));

  function reorderPage(from: number, to: number) {
    configText = moveConfigPage(configText, from, to);
    showNotice("Pages reordered. Save to keep the new order.");
  }

  function deletePage(index: number) {
    const page = configPages[index];
    if (!page) {
      return;
    }
    configText = removeConfigPage(configText, index);
    showNotice(`Deleted the page “${page.title}”. Save to keep the change.`);
  }

  /** Applies one page's form; the file only moves when a value really differs. */
  function applyPageEdit(index: number, edit: ConfigPageEdit) {
    const before = configText;
    configText = updateConfigPage(configText, index, edit);
    if (configText !== before) {
      showNotice("Page settings updated. Save to keep the change.");
    }
  }

  /** The display settings of one page, which win over the file's defaults. */
  function applyPageDisplay(index: number, values: DisplaySettings) {
    const before = configText;
    configText = updateDisplaySettings(configText, index, values);
    if (configText !== before) {
      showNotice("Page settings updated. Save to keep the change.");
    }
  }

  /** Adds an empty page after the last one; the card says what to do next. */
  function addPage(page: NewConfigPage) {
    const before = configText;
    configText = addConfigPage(configText, page);
    if (configText === before) {
      showNotice(`A page already uses the path ${page.path}.`);
      return;
    }
    showNotice(
      `Added the page “${page.title || page.path}”. Add stops to it, then save.`,
    );
  }

  /** The settings every page inherits. */
  function applyDefaults(values: DisplaySettings) {
    const before = configText;
    configText = updateDisplaySettings(configText, "global", values);
    if (configText !== before) {
      showNotice("Defaults updated. Save to keep the change.");
    }
  }

  function deleteStop(pageIndex: number, stopIndex: number) {
    const page = configPages[pageIndex];
    const stop = page?.stops[stopIndex];
    if (!page || !stop) {
      return;
    }
    configText = removeConfigStop(configText, pageIndex, stopIndex);
    showNotice(`Deleted “${stop.name}” from “${page.title}”. Save to keep the change.`);
  }

  /** Puts the page back when it went missing; it is never removed from here. */
  function restoreOnTheRun() {
    configText = addOnTheRunSection(configText);
    showNotice(
      'Next to me is back with its default settings. Adjust them in the text, then save.',
    );
  }

  async function loadExampleConfig() {
    isLoadingExample = true;
    errorMessage = null;
    
    try {
      // Use relative path to work with both root and subdirectory deployments
      const configPath = "./config.example.toml";
      const response = await fetch(configPath);
      if (response.ok) {
        const exampleToml = await response.text();
        configText = exampleToml;
        console.log(`Loaded example config from ${configPath}`);
      } else {
        errorMessage = `Failed to load example config: ${response.status} ${response.statusText}`;
        console.error("Failed to fetch example config:", response.status, response.statusText);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      errorMessage = `Failed to load example config: ${message}`;
      console.error("Failed to load example config:", error);
    } finally {
      isLoadingExample = false;
    }
  }

  async function handleSave() {
    if (!configText.trim()) {
      return;
    }

    // Validate TOML syntax and parsing before saving
    errorMessage = null;
    isSaving = true;

    try {
      // Try to parse the TOML to validate it
      configParser.parseToml(configText);
      
      // If parsing succeeds, call onSave
      await onSave(configText);
      // onSave will close the modal on success
    } catch (error) {
      // Extract error message
      const message = error instanceof Error ? error.message : String(error);
      errorMessage = `Invalid TOML configuration: ${message}`;
      console.error("Config validation failed:", error);
      // Don't close modal, let user fix the error
    } finally {
      isSaving = false;
    }
  }

  /**
   * Leaving with unsaved edits asks once: a mis-tap next to Save should not
   * throw away a reordered page or a new heading.
   */
  function requestCancel() {
    if (configText !== savedText) {
      confirmCancel = true;
      return;
    }
    onCancel();
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === "Escape") {
      requestCancel();
      return;
    }

    if (event.target !== event.currentTarget) {
      return;
    }

    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      requestCancel();
    }
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(configText);
      copySuccess = true;
      setTimeout(() => {
        copySuccess = false;
      }, 2000);
    } catch (error) {
      console.error("Failed to copy to clipboard:", error);
      errorMessage = "Failed to copy to clipboard. Please try manually selecting and copying.";
    }
  }

  async function handlePaste() {
    let text: string;
    try {
      text = (await navigator.clipboard.readText()).trim();
    } catch (error) {
      console.error("Failed to read the clipboard:", error);
      errorMessage = "Could not read the clipboard. Please paste manually.";
      return;
    }

    if (!text) {
      errorMessage = "Clipboard is empty. Please copy a valid TOML config.";
      flashPaste(false);
      return;
    }

    let contentToUse: string;
    try {
      contentToUse = await readPastedConfig(text);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      errorMessage = `Could not load the pasted link: ${message}`;
      flashPaste(false);
      return;
    }

    try {
      configParser.parseToml(contentToUse);
      configText = contentToUse;
      errorMessage = null;
      flashPaste(true);
    } catch (error) {
      console.error("Failed to paste from clipboard:", error);
      errorMessage = "Clipboard does not contain valid TOML configuration.";
      flashPaste(false);
    }
  }

  /**
   * A pasted link is fetched - GitHub's file pages through their raw host, the
   * same way `?config=` is handled. Anything that is not a link is TOML text.
   */
  async function readPastedConfig(text: string): Promise<string> {
    const url = parseHttpUrl(text);
    if (!url) {
      return text;
    }
    return fetchToml(rawConfigUrl(url) ?? url.href);
  }

  function parseHttpUrl(text: string): URL | null {
    try {
      const url = new globalThis.URL(text);
      return url.protocol === "http:" || url.protocol === "https:"
        ? url
        : null;
    } catch {
      return null;
    }
  }

  function flashPaste(success: boolean) {
    pasteSuccess = success;
    pasteError = !success;
    setTimeout(() => {
      pasteSuccess = false;
      pasteError = false;
    }, 2000);
  }

  async function handleWizardComplete(result: WizardResult) {
    // Build TOML config from wizard result
    // Preserve existing layout and only update the target section

    try {
      const existingConfig = configText;

      if (existingConfig.trim()) {
        configParser.parseToml(existingConfig);
      }

      const updatedConfig = applyWizardConfig(existingConfig, result);
      configText = updatedConfig.trim();

      showWizard = false;
      errorMessage = null; // Clear any previous errors
      // Don't auto-save - let user review the generated config first
    } catch (error) {
      errorMessage =
        error instanceof Error ? error.message : "Failed to generate config";
      console.error("Wizard completion error:", error);
    }
  }
</script>

<div
  class="modal-overlay"
  onclick={(event) => {
    if (event.target === event.currentTarget) {
      onCancel();
    }
  }}
  onkeydown={handleKeydown}
  role="button"
  tabindex="0"
  aria-label="Close configuration dialog"
>
  {#if showWizard}
    <ConfigWizard
      onComplete={handleWizardComplete}
      onCancel={() => (showWizard = false)}
      routeStopIdsByPath={wizardContext?.routeStopIdsByPath ?? {}}
      onTheRunDisabled={isOnTheRunRoute(getCurrentRoutePath())}
    />
  {:else}
    <div class="modal-content">
      <div class="modal-header">
        <h2>Configuration</h2>
        <button class="close-button" onclick={requestCancel} aria-label="Close">×</button>
      </div>
      <div class="view-tabs" role="tablist">
        <button
          class="view-tab"
          class:view-tab-active={view === "pages"}
          role="tab"
          aria-selected={view === "pages"}
          onclick={() => (view = "pages")}
        >
          Pages
        </button>
        <button
          class="view-tab"
          class:view-tab-active={view === "toml"}
          role="tab"
          aria-selected={view === "toml"}
          onclick={() => (view = "toml")}
        >
          TOML
        </button>
      </div>
      <div class="modal-body">
      {#if errorMessage}
        <div class="error-message" role="alert">
          {errorMessage}
        </div>
      {/if}
      {#if pendingCleanup}
        <div class="cleanup-review" role="status">
          <p class="cleanup-review-title">Review the clean-up before applying it</p>
          <p>{pendingCleanup.description}</p>
          <div class="cleanup-review-actions">
            <button class="button button-secondary" onclick={cancelCleanup}>Cancel clean-up</button>
            <button class="button button-primary" onclick={applyCleanup}>Apply clean-up</button>
          </div>
        </div>
      {/if}
      {#if notice}
        <div class="config-notice" role="status">
          {notice}
        </div>
      {/if}
      {#if view === "pages"}
        <div class="page-row">
          <div class="page-row-text">
            <strong>Next to me</strong>
            <span class="page-row-hint">
              {hasOnTheRunPage
                ? "The nearby-departures page is part of this config."
                : "The nearby-departures page is missing from this config."}
            </span>
          </div>
          {#if hasOnTheRunPage}
            <button
              class="button button-secondary"
              onclick={openOnTheRunForm}
              disabled={isSaving || isLoadingExample}
              title="Change the radius, the number of departures and the API"
            >
              Edit
            </button>
          {:else}
            <button
              class="button button-primary"
              onclick={restoreOnTheRun}
              disabled={isSaving || isLoadingExample}
              title="Add the nearby-departures page back to the config"
            >
              Restore
            </button>
          {/if}
        </div>

        {#if onTheRunDraft !== null}
          {@const draft = onTheRunDraft}
          <div class="page-row-form">
            <div class="on-the-run-fields">
              {#each ON_THE_RUN_FIELDS as field (field.key)}
                <label class="on-the-run-field">
                  <span class="on-the-run-label">{field.label}</span>
                  {#if field.kind === "boolean"}
                    <input
                      type="checkbox"
                      checked={draft[field.key] === "true"}
                      aria-label={field.label}
                      onchange={(event) =>
                        (draft[field.key] = event.currentTarget.checked
                          ? "true"
                          : "false")}
                    />
                  {:else}
                    <input
                      type={field.kind === "number" ? "number" : "text"}
                      bind:value={draft[field.key]}
                      aria-label={field.label}
                    />
                  {/if}
                  {#if field.hint}
                    <small class="on-the-run-hint">{field.hint}</small>
                  {/if}
                </label>
              {/each}
            </div>
            <div class="page-row-actions">
              <button class="button button-secondary" onclick={() => (onTheRunDraft = null)}>
                Cancel
              </button>
              <button class="button button-primary" onclick={applyOnTheRun}>
                Apply
              </button>
            </div>
          </div>
        {/if}

        <ConfigPages
          pages={configPages}
          defaults={globalDisplay}
          onReorder={reorderPage}
          onRemovePage={deletePage}
          onRemoveStop={deleteStop}
          onApplyPage={applyPageEdit}
          onApplyPageDisplay={applyPageDisplay}
          onApplyDefaults={applyDefaults}
          onAddPage={addPage}
          onAddStops={openWizard}
        />
      {:else}
        <p>Paste a TOML configuration, or a link to one, below:</p>
        <div class="info-links">
          <p>
            <a href="https://github.com/d-led/my-mvg-departures/blob/main/docs/FINDING_STOP_IDS.md" target="_blank" rel="noopener noreferrer">Find station IDs using the project tooling</a>.
          </p>
          <p>
            This is the <a href="https://d-led.github.io/my-mvg-departures/" target="_blank" rel="noopener noreferrer">SPA version</a> of the MVG Departures app. More examples are in the <a href="https://github.com/d-led/my-mvg-departures/blob/main/spa/README.md" target="_blank" rel="noopener noreferrer">README</a>.
          </p>
        </div>
      <div class="textarea-container">
        <div class="textarea-toolbar">
          <button 
            class="icon-button" 
            onclick={handleCopy}
            title={copySuccess ? "Copied!" : "Copy configuration to clipboard"}
            disabled={!configText.trim() || isSaving || isLoadingExample}
            aria-label="Copy configuration"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 115.77 122.88" class="icon">
              <path d="M89.62,13.96v7.73h12.19h0.01v0.02c3.85,0.01,7.34,1.57,9.86,4.1c2.5,2.51,4.06,5.98,4.07,9.82h0.02v0.02 v73.27v0.01h-0.02c-0.01,3.84-1.57,7.33-4.1,9.86c-2.51,2.5-5.98,4.06-9.82,4.07v0.02h-0.02h-61.7H40.1v-0.02 c-3.84-0.01-7.34-1.57-9.86-4.1c-2.5-2.51-4.06-5.98-4.07-9.82h-0.02v-0.02V92.51H13.96h-0.01v-0.02c-3.84-0.01-7.34-1.57-9.86-4.1 c-2.5-2.51-4.06-5.98-4.07-9.82H0v-0.02V13.96v-0.01h0.02c0.01-3.85,1.58-7.34,4.1-9.86c2.51-2.5,5.98-4.06,9.82-4.07V0h0.02h61.7 h0.01v0.02c3.85,0.01,7.34,1.57,9.86,4.1c2.5,2.51,4.06,5.98,4.07,9.82h0.02V13.96L89.62,13.96z M79.04,21.69v-7.73v-0.02h0.02 c0-0.91-0.39-1.75-1.01-2.37c-0.61-0.61-1.46-1-2.37-1v0.02h-0.01h-61.7h-0.02v-0.02c-0.91,0-1.75,0.39-2.37,1.01 c-0.61,0.61-1,1.46-1,2.37h0.02v0.01v64.59v0.02h-0.02c0,0.91,0.39,1.75,1.01,2.37c0.61,0.61,1.46,1,2.37,1v-0.02h0.01h12.19V35.65 v-0.01h0.02c0.01-3.85,1.58-7.34,4.1-9.86c2.51-2.5,5.98-4.06,9.82-4.07v-0.02h0.02H79.04L79.04,21.69z M105.18,108.92V35.65v-0.02 h0.02c0-0.91-0.39-1.75-1.01-2.37c-0.61-0.61-1.46-1-2.37-1v0.02h-0.01h-61.7h-0.02v-0.02c-0.91,0-1.75,0.39-2.37,1.01 c-0.61,0.61-1,1.46-1,2.37h0.02v0.01v73.27v0.02h-0.02c0,0.91,0.39,1.75,1.01,2.37c0.61,0.61,1.46,1,2.37,1v-0.02h0.01h61.7h0.02 v0.02c0.91,0,1.75-0.39,2.37-1.01c0.61-0.61,1-1.46,1-2.37h-0.02V108.92L105.18,108.92z"/>
            </svg>
            {#if copySuccess}
              <span class="success-indicator">✓</span>
            {/if}
          </button>
          <button 
            class="icon-button" 
            onclick={handlePaste}
            title={pasteSuccess ? "Pasted!" : "Paste configuration from clipboard"}
            disabled={isSaving || isLoadingExample}
            aria-label="Paste configuration"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 399 512.02" class="icon">
              <path d="M96.59 35.73h34.9C133.94 15.58 150.2 0 169.92 0c19.6 0 35.77 15.37 38.39 35.31l35.47.42c2.37 0 4.26 1.89 4.26 4.26V87c0 2.36-1.89 4.26-4.26 4.26H96.63c-2.31 0-4.26-1.9-4.26-4.26V39.99c-.04-2.37 1.86-4.26 4.22-4.26zm108.07 301.63c-5.44 0-9.86-4.42-9.86-9.87 0-5.44 4.42-9.86 9.86-9.86h124.93c5.45 0 9.86 4.42 9.86 9.86 0 5.45-4.41 9.87-9.86 9.87H204.66zm103.16-170.67h.88c3.12 0 5.9 1.44 7.7 3.7l80.02 87.86a9.845 9.845 0 0 1 2.56 6.62l.02 2.66v223.28c0 5.81-2.41 11.13-6.25 14.97s-9.15 6.24-14.96 6.24H156.47c-5.77 0-11.08-2.39-14.94-6.24l-.04-.04c-3.84-3.87-6.23-9.14-6.23-14.93V187.7c0-5.83 2.38-11.14 6.22-14.98s9.15-6.23 14.99-6.23h149.37c.68 0 1.34.07 1.98.2zm71.46 110.8c-43.74-1.7-65.42-3.27-77.68-16.13-12.27-12.88-11.51-32.56-10.03-70.26l.19-4.88H156.47c-.41 0-.78.17-1.05.44-.27.26-.44.64-.44 1.04v303.11c0 .41.16.78.41 1.03l.04.04c.26.26.63.42 1.04.42h221.32c.37 0 .74-.18 1.02-.46s.47-.65.47-1.03V277.49zm-68.25-80.91c-1.13 29.16-1.41 44.68 4.82 51.22 6.15 6.45 21.33 8.17 50.65 9.5l-55.47-60.72zM204.66 447.87c-5.44 0-9.86-4.41-9.86-9.86 0-5.44 4.42-9.86 9.86-9.86h124.93c5.45 0 9.86 4.42 9.86 9.86 0 5.45-4.41 9.86-9.86 9.86H204.66zm0-55.26c-5.44 0-9.86-4.41-9.86-9.86 0-5.44 4.42-9.86 9.86-9.86h124.93c5.45 0 9.86 4.42 9.86 9.86 0 5.45-4.41 9.86-9.86 9.86H204.66zm-104.29 7.49c6.93 0 12.55 5.62 12.55 12.55 0 6.92-5.62 12.55-12.55 12.55H39.33c-10.72 0-20.58-4.45-27.75-11.61C4.45 406.51 0 396.69 0 385.86V91.56C0 80.73 4.42 70.9 11.54 63.78l.84-.77c7.05-6.66 16.55-10.77 26.95-10.77h32.46v25.11H39.33c-3.68 0-7.05 1.4-9.57 3.69l-.47.49c-2.58 2.58-4.19 6.14-4.19 10.03v294.3c0 3.87 1.63 7.42 4.21 10.01v.05c2.58 2.58 6.14 4.18 10.02 4.18h61.04zM268.61 52.24h32.44c10.79 0 20.6 4.45 27.72 11.56 7.17 7.16 11.62 17.02 11.62 27.76v29.91c0 6.93-5.62 12.55-12.55 12.55-6.93 0-12.55-5.62-12.55-12.55V91.56c0-3.88-1.6-7.44-4.17-10.01-2.58-2.58-6.15-4.2-10.07-4.2h-32.44V52.24zm-99.13-33.96c11.15 0 20.18 9.03 20.18 20.18s-9.03 20.19-20.18 20.19-20.19-9.04-20.19-20.19c0-11.15 9.04-20.18 20.19-20.18z"/>
            </svg>
            {#if pasteSuccess}
              <span class="success-indicator">✓</span>
            {:else if pasteError}
              <span class="error-indicator">✗</span>
            {/if}
          </button>
          <button
            class="icon-button"
            onclick={openTweak}
            disabled={!configText.trim() || isSaving || isLoadingExample}
            title="Tweak numeric and display values"
            aria-label="Tweak display values"
          >
            <img src="assets/settings-line-icon.svg" alt="" class="icon" />
          </button>
          <button
            class="icon-button"
            onclick={() => (showFullscreenEditor = true)}
            title="Expand editor for mobile editing"
            aria-label="Expand editor"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="icon"><path d="M4 4h7V2H2v9h2V4zm16 0v7h2V2h-9v2h7zm0 16h-7v2h9v-9h-2v7zM4 20v-7H2v9h9v-2H4z"/></svg>
          </button>
          <button
            class="toolbar-text-button"
            onclick={previewCleanup}
            disabled={!configText.trim() || isSaving || isLoadingExample}
            title="Remove the sections and settings the SPA never reads"
          >
            Clean up
          </button>
        </div>
        <textarea
          bind:value={configText}
          class="config-textarea"
          class:error={!!errorMessage}
          placeholder="Paste TOML config here..."
          readonly={showFullscreenEditor}
        ></textarea>
        {#if showFullscreenEditor}
          <div class="fullscreen-editor-overlay" role="dialog" aria-modal="true" tabindex="-1" onkeydown={e => { if (e.key === 'Escape') showFullscreenEditor = false; }}>
            <div class="fullscreen-editor-content">
              <button class="button button-primary fullscreen-close" onclick={() => (showFullscreenEditor = false)}>
                Done
              </button>
              <textarea
                bind:value={configText}
                class="fullscreen-textarea"
                spellcheck="false"
              ></textarea>
            </div>
          </div>
        {/if}
        {#if showTweakOverlay}
          <div class="tweak-overlay" role="dialog" aria-modal="true" aria-label="Tweak display values" tabindex="-1" onkeydown={e => { if (e.key === 'Escape') closeTweakAndApply(); else if (e.key === 'Enter') { e.preventDefault(); closeTweakAndApply(); } }}>
            <div class="tweak-overlay-content">
              <div class="tweak-close-bar">
                <div class="tweak-filter-wrap">
                  <input
                    type="text"
                    class="tweak-filter-input"
                    placeholder="Filter (space-separated, all must match)"
                    bind:value={tweakFilterQuery}
                    bind:this={tweakFilterInputEl}
                    aria-label="Filter entries"
                  />
                  {#if tweakFilterQuery.trim()}
                    <button
                      type="button"
                      class="tweak-filter-clear"
                      onmousedown={(e) => e.preventDefault()}
                      onclick={clearTweakFilter}
                      aria-label="Clear filter"
                      title="Clear filter"
                    >
                      ×
                    </button>
                  {/if}
                </div>
                <button class="button button-primary tweak-close" onclick={closeTweakAndApply}>
                  Ok
                </button>
              </div>
              <div class="tweak-list">
                {#if tweakSections.length === 0}
                  <p class="tweak-empty">No sections found. Add at least one TOML section (a line starting with [).</p>
                {:else}
                  {#each tweakSections as section, sectionIdx (sectionIdx)}
                    {@const hasVisible = tweakSectionHasVisibleEntries(section, tweakFilterParts, sectionIdx)}
                    {#if hasVisible}
                      <section class="tweak-section">
                        <h3 class="tweak-section-title">
                          {section.heading}
                          {#if section.heading === "[[routes.stops]]" || section.heading === "[[stops]]"}
                            {@const stationNameEntry = section.entries.find((e) => e.key === "station_name")}
                            {#if stationNameEntry?.value}
                              <span class="tweak-section-context"> {stationNameEntry.value}</span>
                            {/if}
                          {/if}
                        </h3>
                        <ul class="tweak-entries">
                          {#each section.entries as entry (`${sectionIdx}-${entry.lineIndex}`)}
                            {#if tweakShowEntry(section, entry, tweakFilterParts, sectionIdx)}
                              <li class="tweak-entry">
                                <label class="tweak-key" for="tweak-input-{sectionIdx}-{entry.lineIndex}">
                                  {entry.key}
                                  {#if tweakDuplicateKeys.has(entry.key)}
                                    <span class="tweak-key-context"> [{section.heading}]</span>
                                  {/if}
                                </label>
                                <input
                                  id="tweak-input-{sectionIdx}-{entry.lineIndex}"
                                  type="text"
                                  class="tweak-value"
                                  bind:value={entry.value}
                                  onfocus={(e) => {
                                    lastTweakValueFocusedEl = e.currentTarget;
                                  }}
                                  aria-label={tweakDuplicateKeys.has(entry.key) ? `${entry.key} in ${section.heading}` : entry.key}
                                />
                              </li>
                            {/if}
                          {/each}
                        </ul>
                      </section>
                    {/if}
                  {/each}
                {/if}
              </div>
            </div>
          </div>
        {/if}
      </div>
      {/if}
    </div>
    <div class="modal-footer">
      <span class="build-sha">__BUILD_SHA__</span>
      <div class="modal-footer-actions">
        {#if confirmCancel}
          <span class="discard-question">Discard the changes?</span>
          <button class="button button-secondary" onclick={() => (confirmCancel = false)}>
            Keep editing
          </button>
          <button class="button button-danger" onclick={onCancel}>
            Discard changes
          </button>
        {:else}
          <button 
            class="button button-example" 
            onclick={() => loadExampleConfig()} 
            disabled={isSaving || isLoadingExample}
            title="Load example configuration"
          >
            {isLoadingExample ? "Loading..." : "Example"}
          </button>
          <button class="button button-secondary" onclick={requestCancel} disabled={isSaving || isLoadingExample}>Cancel</button>
          <button class="button button-primary" onclick={handleSave} disabled={!configText.trim() || isSaving || isLoadingExample}>
            {isSaving ? "Saving..." : "Save"}
          </button>
        {/if}
      </div>
    </div>
  </div>
  {/if}
</div>

<style>
  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10000;
  }

  .view-tabs {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
    border-bottom: 2px solid #e5e7eb;
    flex-shrink: 0;
  }

  :global([data-theme="dark"]) .view-tabs {
    border-bottom-color: #374151;
  }

  .view-tab {
    padding: 0.5rem 0.75rem;
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
    cursor: pointer;
    font-weight: 500;
    color: #6b7280;
  }

  .view-tab:hover {
    color: #111827;
  }

  :global([data-theme="dark"]) .view-tab {
    color: #9ca3af;
  }

  :global([data-theme="dark"]) .view-tab:hover {
    color: #f9fafb;
  }

  .view-tab-active {
    color: #087bc4;
    border-bottom-color: #087bc4;
  }

  :global([data-theme="dark"]) .view-tab-active {
    color: #60a5fa;
    border-bottom-color: #60a5fa;
  }

  .toolbar-text-button {
    padding: 0.25rem 0.5rem;
    border: 1px solid #d1d5db;
    border-radius: 0.375rem;
    background: white;
    font-size: 0.8rem;
    cursor: pointer;
    white-space: nowrap;
  }

  .toolbar-text-button:hover:not(:disabled) {
    background: #f3f4f6;
  }

  .toolbar-text-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  :global([data-theme="dark"]) .toolbar-text-button {
    background: #374151;
    border-color: #4b5563;
    color: #e5e7eb;
  }

  /* Lock body scroll when fullscreen editor is open (prevents scroll bleed on mobile) - CSS only via :has() */
  :global(body:has(.fullscreen-editor-overlay)) {
    overflow: hidden;
    overscroll-behavior: none;
  }

  .fullscreen-editor-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0,0,0,0.8);
    z-index: 11000;
    display: flex;
    align-items: stretch;
    justify-content: stretch;
    width: 100vw;
    height: 100vh;
    /* iOS counts the address bar into 100vh; dvh is the visible height. */
    height: 100dvh;
    overflow: hidden;
    overscroll-behavior: contain;
    -webkit-overflow-scrolling: touch;
  }

  .fullscreen-editor-content {
    background: white;
    border-radius: 0;
    padding: 8px;
    width: 100vw;
    height: 100vh;
    height: 100dvh;
    display: flex;
    flex-direction: column;
    box-shadow: none;
    border: 4px solid #087BC4;
    box-sizing: border-box;
    gap: 8px;
    overflow: hidden;
    overscroll-behavior: contain;
    min-height: 0;
  }

  @media (min-width: 600px) {
    .fullscreen-editor-content {
      padding: 24px;
    }
  }

  :global([data-theme="dark"]) .fullscreen-editor-content {
    border: 4px solid #60a5fa;
  }

  .fullscreen-close {
    align-self: flex-end;
    min-width: 100px;
    font-size: 1.1rem;
    margin: 1rem;
    z-index: 1;
  }

  .fullscreen-textarea {
    flex: 1 1 0;
    width: 100%;
    height: 100%;
    min-height: 0;
    font-family: monospace;
    font-size: 1rem;
    padding: 0.5rem;
    border: none;
    border-radius: 0;
    resize: none;
    box-sizing: border-box;
    background: #f9fafb;
    color: #111827;
    outline: none;
    overflow-x: auto;
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
    overscroll-behavior: contain;
    white-space: pre;
    word-break: normal;
  }

  .tweak-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.8);
    z-index: 11000;
    display: flex;
    align-items: stretch;
    justify-content: stretch;
    width: 100vw;
    height: 100vh;
    height: 100dvh;
  }

  .tweak-overlay-content {
    background: white;
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    padding: 8px;
    box-sizing: border-box;
    gap: 0;
    border: 4px solid #087BC4;
    overflow: hidden;
    min-height: 0;
  }

  :global([data-theme="dark"]) .tweak-overlay-content {
    background: #1d232a;
    color: #f9fafb;
    border-color: #60a5fa;
  }

  .tweak-close-bar {
    position: sticky;
    top: 0;
    z-index: 2;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 8px 0;
    background: inherit;
  }

  .tweak-filter-wrap {
    flex: 1;
    min-width: 0;
    position: relative;
    display: flex;
    align-items: center;
  }

  .tweak-filter-input {
    width: 100%;
    min-width: 0;
    padding: 0.5rem 0.75rem;
    padding-right: 2rem;
    font-size: 1rem;
    border: 1px solid #d1d5db;
    border-radius: 0.375rem;
    box-sizing: border-box;
  }

  .tweak-filter-input::placeholder {
    color: #9ca3af;
  }

  :global([data-theme="dark"]) .tweak-filter-input {
    background: #111827;
    border-color: #4b5563;
    color: #f9fafb;
  }

  :global([data-theme="dark"]) .tweak-filter-input::placeholder {
    color: #6b7280;
  }

  .tweak-filter-clear {
    position: absolute;
    right: 0.4rem;
    top: 50%;
    transform: translateY(-50%);
    width: 1.5rem;
    height: 1.5rem;
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.25rem;
    line-height: 1;
    color: #6b7280;
    background: transparent;
    border: none;
    border-radius: 0.25rem;
    cursor: pointer;
  }

  .tweak-filter-clear:hover {
    color: #111827;
    background: #e5e7eb;
  }

  :global([data-theme="dark"]) .tweak-filter-clear {
    color: #9ca3af;
  }

  :global([data-theme="dark"]) .tweak-filter-clear:hover {
    color: #f9fafb;
    background: #4b5563;
  }

  .tweak-close {
    min-width: 100px;
    font-size: 1.1rem;
    flex-shrink: 0;
  }

  .tweak-list {
    flex: 1 1 auto;
    display: flex;
    flex-direction: column;
    gap: 0.9rem;
    padding-bottom: 1rem;
    overflow: auto;
    min-height: 0;
  }

  .tweak-empty {
    margin: 0;
    color: #6b7280;
  }

  :global([data-theme="dark"]) .tweak-empty {
    color: #9ca3af;
  }

  .tweak-section {
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
  }

  .tweak-section-title {
    margin: 0;
    font-size: 1.1rem;
    font-weight: 700;
  }

  .tweak-section-context {
    font-weight: 400;
    color: #6b7280;
    font-size: 0.95rem;
  }

  :global([data-theme="dark"]) .tweak-section-context {
    color: #9ca3af;
  }

  .tweak-entries {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
  }

  .tweak-entry {
    display: grid;
    grid-template-rows: auto auto;
    gap: 0.15rem;
    padding: 0.3rem 0;
    border-bottom: 1px solid #e5e7eb;
  }

  :global([data-theme="dark"]) .tweak-entry {
    border-bottom-color: #374151;
  }

  .tweak-key {
    font-size: 0.9rem;
    font-weight: 500;
    color: #374151;
  }

  .tweak-key-context {
    font-weight: 400;
    color: #6b7280;
    font-size: 0.85rem;
  }

  :global([data-theme="dark"]) .tweak-key {
    color: #9ca3af;
  }

  :global([data-theme="dark"]) .tweak-key-context {
    color: #6b7280;
  }

  .tweak-value {
    width: 100%;
    min-width: 0;
    padding: 0.3rem;
    font-size: 1rem;
    border: 1px solid #d1d5db;
    border-radius: 0.375rem;
    box-sizing: border-box;
  }

  :global([data-theme="dark"]) .tweak-value {
    background: #111827;
    border-color: #4b5563;
    color: #f9fafb;
  }

  .modal-content {
    background: white;
    border-radius: 0.5rem;
    padding: 1.5rem;
    max-width: 90vw;
    max-height: 90vh;
    min-height: 500px;
    width: 800px;
    display: flex;
    flex-direction: column;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
    overflow: hidden; /* Prevent content from overflowing */
  }

  /**
   * On a phone the dialog is the editor: it takes the whole screen and the
   * chrome around the text area shrinks, so typing does not happen in a sliver.
   */
  @media (max-width: 640px), (max-height: 620px) {
    .modal-content {
      width: 100vw;
      max-width: 100vw;
      height: 100dvh;
      max-height: 100dvh;
      min-height: 0;
      border-radius: 0;
      padding: 0.75rem;
    }

    .modal-header {
      margin-bottom: 0.5rem;
    }

    .modal-header h2 {
      font-size: 1.25rem;
    }

    .view-tabs {
      margin-bottom: 0.5rem;
    }

    .view-tab {
      padding: 0.4rem 0.6rem;
      font-size: 0.9rem;
    }

    .page-row {
      padding: 0.4rem 0.6rem;
      margin-bottom: 0.5rem;
    }

    .modal-body > p {
      font-size: 0.85rem;
      margin-bottom: 0.4rem;
    }

    .info-links {
      padding: 0.5rem;
      margin-bottom: 0.5rem;
      font-size: 0.8rem;
    }

    .config-textarea {
      font-size: 0.8rem;
      padding: 0.5rem;
    }

    .modal-body {
      margin-bottom: 0.5rem;
    }

    .modal-footer {
      padding-top: 0.25rem;
    }

    .build-sha {
      display: none;
    }
  }

  :global([data-theme="dark"]) .modal-content {
    background: #1d232a;
    color: #f9fafb;
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }

  .modal-header h2 {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 700;
  }

  .close-button {
    background: none;
    border: none;
    font-size: 2rem;
    cursor: pointer;
    padding: 0;
    width: 2rem;
    height: 2rem;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #6b7280;
  }

  .close-button:hover {
    color: #111827;
  }

  :global([data-theme="dark"]) .close-button {
    color: #9ca3af;
  }

  :global([data-theme="dark"]) .close-button:hover {
    color: #f9fafb;
  }

  .modal-body {
    flex: 1 1 auto;
    display: flex;
    flex-direction: column;
    min-height: 0; /* Critical for flexbox children to shrink */
    margin-bottom: 1rem;
    overflow: hidden; /* Prevent body from scrolling, let textarea handle it */
  }

  .modal-body p {
    margin: 0 0 0.75rem 0;
    flex-shrink: 0; /* Don't shrink the label */
  }

  .info-links {
    margin-bottom: 0.75rem;
    padding: 0.75rem;
    background-color: #f3f4f6;
    border-radius: 0.375rem;
    font-size: 0.875rem;
    flex-shrink: 0;
  }

  :global([data-theme="dark"]) .info-links {
    background-color: #374151;
  }

  .info-links p {
    margin: 0.25rem 0;
  }

  .info-links a {
    color: #087BC4;
    text-decoration: underline;
  }

  .info-links a:hover {
    color: #0669a3;
  }

  :global([data-theme="dark"]) .info-links a {
    color: #60a5fa;
  }

  :global([data-theme="dark"]) .info-links a:hover {
    color: #93c5fd;
  }

  .error-message {
    background-color: #fee2e2;
    border: 1px solid #fca5a5;
    border-radius: 0.375rem;
    padding: 0.75rem;
    margin-bottom: 0.75rem;
    color: #991b1b;
    font-size: 0.875rem;
    flex-shrink: 0;
  }

  :global([data-theme="dark"]) .error-message {
    background-color: #7f1d1d;
    border-color: #dc2626;
    color: #fca5a5;
  }

  .cleanup-review {
    background-color: #eff6ff;
    border: 1px solid #93c5fd;
    border-radius: 0.375rem;
    padding: 0.75rem;
    margin-bottom: 0.75rem;
    color: #1e3a8a;
    font-size: 0.875rem;
    flex-shrink: 0;
  }

  :global([data-theme="dark"]) .cleanup-review {
    background-color: #1e3a8a;
    border-color: #3b82f6;
    color: #dbeafe;
  }

  .cleanup-review-title {
    font-weight: 600;
    margin-bottom: 0.25rem;
  }

  .cleanup-review-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
    margin-top: 0.5rem;
  }

  .config-notice {
    background-color: #ecfdf5;
    border: 1px solid #6ee7b7;
    border-radius: 0.375rem;
    padding: 0.75rem;
    margin-bottom: 0.75rem;
    color: #065f46;
    font-size: 0.875rem;
    flex-shrink: 0;
  }

  :global([data-theme="dark"]) .config-notice {
    background-color: #064e3b;
    border-color: #059669;
    color: #6ee7b7;
  }

  .page-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
    border: 1px solid #e5e7eb;
    border-radius: 0.5rem;
    padding: 0.5rem 0.75rem;
    margin-bottom: 0.75rem;
    background: #f9fafb;
  }

  :global([data-theme="dark"]) .page-row {
    border-color: #374151;
    background: #111827;
  }

  .page-row-text {
    display: flex;
    flex-direction: column;
    flex: 1 1 12rem;
    min-width: 0;
    font-size: 0.875rem;
  }

  .page-row-hint {
    color: #6b7280;
    font-size: 0.8rem;
  }

  :global([data-theme="dark"]) .page-row-hint {
    color: #9ca3af;
  }

  .page-row-form {
    border: 1px solid #e5e7eb;
    border-top: none;
    border-radius: 0 0 0.5rem 0.5rem;
    padding: 0.5rem 0.75rem 0.75rem;
    margin-top: -0.75rem;
    margin-bottom: 0.75rem;
    background: #f9fafb;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  :global([data-theme="dark"]) .page-row-form {
    border-color: #374151;
    background: #111827;
  }

  .on-the-run-fields {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
    gap: 0.5rem 0.75rem;
    min-width: 0;
  }

  .on-the-run-field {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    font-size: 0.8rem;
    min-width: 0;
  }

  .on-the-run-label {
    font-weight: 500;
  }

  .on-the-run-field input[type="number"],
  .on-the-run-field input[type="text"] {
    padding: 0.3rem 0.45rem;
    border: 1px solid #d1d5db;
    border-radius: 0.375rem;
    font-size: 0.85rem;
    width: 100%;
    box-sizing: border-box;
  }

  .on-the-run-field input[type="checkbox"] {
    width: 1.1rem;
    height: 1.1rem;
  }

  :global([data-theme="dark"]) .on-the-run-field input[type="number"],
  :global([data-theme="dark"]) .on-the-run-field input[type="text"] {
    background: #1f2937;
    border-color: #4b5563;
    color: #e5e7eb;
  }

  .on-the-run-hint {
    color: #6b7280;
    font-size: 0.72rem;
  }

  :global([data-theme="dark"]) .on-the-run-hint {
    color: #9ca3af;
  }

  .page-row-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
  }

  .discard-question {
    align-self: center;
    font-size: 0.85rem;
    color: #6b7280;
  }

  :global([data-theme="dark"]) .discard-question {
    color: #9ca3af;
  }

  .button-danger {
    background-color: #dc2626;
    color: white;
  }

  .textarea-container {
    flex: 1 1 auto;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }

  .textarea-toolbar {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
    flex-shrink: 0;
  }

  .icon-button {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.5rem;
    background-color: #f3f4f6;
    border: 1px solid #d1d5db;
    border-radius: 0.375rem;
    cursor: pointer;
    transition: all 0.2s;
    position: relative;
  }

  .icon-button:hover:not(:disabled) {
    background-color: #e5e7eb;
    border-color: #9ca3af;
  }

  .icon-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  :global([data-theme="dark"]) .icon-button {
    background-color: #374151;
    border-color: #4b5563;
  }

  :global([data-theme="dark"]) .icon-button:hover:not(:disabled) {
    background-color: #4b5563;
    border-color: #6b7280;
  }

  .icon {
    width: 1.25rem;
    height: 1.25rem;
    fill: #111827;
  }

  .icon-button img.icon {
    object-fit: contain;
    width: 1.5rem;
    height: 1.5rem;
  }

  :global([data-theme="dark"]) .icon-button img.icon {
    filter: invert(1);
  }

  :global([data-theme="dark"]) .icon {
    fill: #f9fafb;
  }

  .success-indicator {
    color: #16a34a;
    font-weight: bold;
    font-size: 1rem;
  }

  .error-indicator {
    color: #dc2626;
    font-weight: bold;
    font-size: 1rem;
  }

  :global([data-theme="dark"]) .success-indicator {
    color: #4ade80;
  }

  :global([data-theme="dark"]) .error-indicator {
    color: #f87171;
  }

  .config-textarea.error {
    border-color: #dc2626;
  }

  :global([data-theme="dark"]) .config-textarea.error {
    border-color: #f87171;
  }

  .config-textarea {
    width: 100%;
    flex: 1 1 auto; /* Fill available space in modal-body */
    min-height: 0; /* Critical for flexbox to work */
    font-family: monospace;
    font-size: 0.875rem;
    padding: 0.75rem;
    border: 1px solid #d1d5db;
    border-radius: 0.375rem;
    resize: none; /* Disable manual resize, let flexbox handle it */
    box-sizing: border-box;
    overflow-y: auto; /* Scroll inside textarea if content is too long */
  }

  :global([data-theme="dark"]) .config-textarea {
    background: #111827;
    color: #f9fafb;
    border-color: #374151;
  }

  .modal-footer {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-shrink: 0;
    margin-top: auto;
  }

  .build-sha {
    font-size: 0.75rem;
    color: #565f89;
    align-self: center;
    margin-right: auto;
  }

  .modal-footer-actions {
    margin-left: auto;
    display: flex;
    gap: 0.75rem;
  }

  @media (max-width: 420px) {
    .modal-footer {
      flex-direction: column;
      align-items: stretch;
      gap: 0.5rem;
    }

    .build-sha {
      margin-right: 0;
      order: -1;
    }

    .modal-footer-actions {
      margin-left: 0;
      justify-content: flex-end;
    }
  }

  :global([data-theme="dark"]) .build-sha {
    color: #6b7280;
  }

  .button-example {
    background-color: #f3f4f6;
    color: #111827;
    border: 1px solid #d1d5db;
  }

  .button-example:hover:not(:disabled) {
    background-color: #e5e7eb;
    border-color: #9ca3af;
  }

  :global([data-theme="dark"]) .button-example {
    background-color: #374151;
    color: #f9fafb;
    border-color: #4b5563;
  }

  :global([data-theme="dark"]) .button-example:hover:not(:disabled) {
    background-color: #4b5563;
    border-color: #6b7280;
  }

  .button {
    padding: 0.5rem 1rem;
    border-radius: 0.375rem;
    font-weight: 500;
    cursor: pointer;
    border: none;
    transition: background-color 0.2s;
  }

  .button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .button-primary {
    background-color: #087BC4;
    color: white;
  }

  .button-primary:hover:not(:disabled) {
    background-color: #0669a3;
  }

  .button-secondary {
    background-color: #e5e7eb;
    color: #111827;
  }

  .button-secondary:hover {
    background-color: #d1d5db;
  }

  :global([data-theme="dark"]) .button-secondary {
    background-color: #374151;
    color: #f9fafb;
  }

  :global([data-theme="dark"]) .button-secondary:hover {
    background-color: #4b5563;
  }
</style>
