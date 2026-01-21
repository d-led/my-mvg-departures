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
  const configStorage = new LocalStorageConfigStorage();
  const configParser = new ConfigParser();

  // Load raw TOML from storage when modal opens
  $effect(async () => {
    const storedToml = await configStorage.getConfigToml();
    configText = storedToml || "";
    errorMessage = null; // Clear error when loading
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
      const response = await fetch("/config.example.toml");
      if (response.ok) {
        const exampleToml = await response.text();
        configText = exampleToml;
        console.log("Loaded example config from /config.example.toml");
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
    }
  }
</script>

<div class="modal-overlay" onclick={onCancel} onkeydown={handleKeydown}>
  <div class="modal-content" onclick={(e) => e.stopPropagation()}>
    <div class="modal-header">
      <h2>Configuration</h2>
      <button class="close-button" onclick={onCancel} aria-label="Close">×</button>
    </div>
    <div class="modal-body">
      <p>Paste your TOML configuration below:</p>
      {#if errorMessage}
        <div class="error-message" role="alert">
          {errorMessage}
        </div>
      {/if}
      <textarea
        bind:value={configText}
        class="config-textarea"
        class:error={!!errorMessage}
        placeholder="Paste TOML config here..."
      ></textarea>
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

  [data-theme="dark"] .modal-content {
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

  [data-theme="dark"] .close-button {
    color: #9ca3af;
  }

  [data-theme="dark"] .close-button:hover {
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

  [data-theme="dark"] .error-message {
    background-color: #7f1d1d;
    border-color: #dc2626;
    color: #fca5a5;
  }

  .config-textarea.error {
    border-color: #dc2626;
  }

  [data-theme="dark"] .config-textarea.error {
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

  [data-theme="dark"] .config-textarea {
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

  [data-theme="dark"] .button-example {
    background-color: #374151;
    color: #f9fafb;
    border-color: #4b5563;
  }

  [data-theme="dark"] .button-example:hover:not(:disabled) {
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

  [data-theme="dark"] .button-secondary {
    background-color: #374151;
    color: #f9fafb;
  }

  [data-theme="dark"] .button-secondary:hover {
    background-color: #4b5563;
  }
</style>
