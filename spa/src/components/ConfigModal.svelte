<script lang="ts">
  import { LocalStorageConfigStorage } from "../adapters/storage/local-storage-config-storage.js";
  import { ConfigParser } from "../adapters/config/config-parser.js";

  let {
    onSave,
    onCancel,
  }: {
    onSave: (config: string) => Promise<void>;
    onCancel: () => void;
  } = $props();

  let configText = $state("");
  let errorMessage = $state<string | null>(null);
  let isSaving = $state(false);
  let isLoadingExample = $state(false);
  let copySuccess = $state(false);
  let pasteSuccess = $state(false);
  let pasteError = $state(false);
  const configStorage = new LocalStorageConfigStorage();
  const configParser = new ConfigParser();

  async function loadStoredConfig(): Promise<void> {
    const storedToml = await configStorage.getConfigToml();
    configText = storedToml || "";
    errorMessage = null; // Clear error when loading
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
  });

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

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === "Escape") {
      onCancel();
      return;
    }

    if (event.target !== event.currentTarget) {
      return;
    }

    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onCancel();
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
    try {
      const text = await navigator.clipboard.readText();
      const trimmed = text.trim();
      if (!trimmed) {
        errorMessage = "Clipboard is empty. Please copy a valid TOML config.";
        pasteError = true;
        setTimeout(() => {
          pasteError = false;
        }, 2000);
        return;
      }

      // If the clipboard contains a gist raw URL from gist.githubusercontent.com,
      // fetch the contents and use that as the config text. Use URL constructor
      // to validate the URL safely.
      let contentToUse = trimmed;
      try {
        const maybeUrl = new URL(trimmed);
        if (maybeUrl.hostname === "gist.githubusercontent.com") {
          try {
            const resp = await fetch(maybeUrl.href);
            if (!resp.ok) {
              throw new Error(`Failed to fetch gist: ${resp.status} ${resp.statusText}`);
            }
            const fetched = await resp.text();
            if (fetched.trim()) {
              contentToUse = fetched;
            } else {
              throw new Error("Fetched gist is empty");
            }
          } catch (fetchErr) {
            // If gist fetch fails, surface a helpful error and abort paste.
            console.error("Failed to fetch gist URL:", fetchErr);
            const message = fetchErr instanceof Error ? fetchErr.message : String(fetchErr);
            errorMessage = `Failed to fetch gist URL: ${message}`;
            pasteError = true;
            setTimeout(() => {
              pasteError = false;
            }, 2000);
            return;
          }
        }
      } catch (urlErr) {
        // Not a valid URL — ignore and continue with clipboard text as-is.
      }

      // Validate TOML content (either fetched content or raw clipboard text)
      configParser.parseToml(contentToUse);
      configText = contentToUse;
      pasteError = false;
      pasteSuccess = true;
      setTimeout(() => {
        pasteSuccess = false;
      }, 2000);
    } catch (error) {
      console.error("Failed to paste from clipboard:", error);
      const message = error instanceof Error ? error.message : String(error);
      errorMessage = message.includes("Invalid TOML")
        ? message
        : "Clipboard does not contain valid TOML configuration.";
      pasteError = true;
      setTimeout(() => {
        pasteError = false;
      }, 2000);
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
  <div class="modal-content">
    <div class="modal-header">
      <h2>Configuration</h2>
      <button class="close-button" onclick={onCancel} aria-label="Close">×</button>
    </div>
    <div class="modal-body">
      <p>Paste your TOML configuration below:</p>
      <div class="info-links">
        <p>
          <a href="https://github.com/d-led/my-mvg-departures/blob/main/docs/FINDING_STOP_IDS.md" target="_blank" rel="noopener noreferrer">Find station IDs using the project tooling</a>.
        </p>
        <p>
          This is the <a href="https://d-led.github.io/my-mvg-departures/" target="_blank" rel="noopener noreferrer">SPA version</a> of the MVG Departures app.
        </p>
      </div>
      {#if errorMessage}
        <div class="error-message" role="alert">
          {errorMessage}
        </div>
      {/if}
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
        </div>
        <textarea
          bind:value={configText}
          class="config-textarea"
          class:error={!!errorMessage}
          placeholder="Paste TOML config here..."
        ></textarea>
      </div>
    </div>
    <div class="modal-footer">
      <button 
        class="button button-example" 
        onclick={loadExampleConfig} 
        disabled={isSaving || isLoadingExample}
        title="Load example configuration"
      >
        {isLoadingExample ? "Loading..." : "Example"}
      </button>
      <button class="button button-secondary" onclick={onCancel} disabled={isSaving || isLoadingExample}>Cancel</button>
      <button class="button button-primary" onclick={handleSave} disabled={!configText.trim() || isSaving || isLoadingExample}>
        {isSaving ? "Saving..." : "Save"}
      </button>
    </div>
  </div>
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
    justify-content: flex-end;
    gap: 0.75rem;
    flex-shrink: 0; /* Don't shrink the footer */
    margin-top: auto; /* Push footer to bottom */
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
