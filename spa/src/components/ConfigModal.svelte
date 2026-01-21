<script lang="ts">
  import { onMount } from "svelte";

  let {
    currentConfig = null,
    onSave,
    onCancel,
  }: {
    currentConfig?: unknown;
    onSave: (config: string) => void;
    onCancel: () => void;
  } = $props();

  let configText = $state("");

  onMount(() => {
    // Load current config as TOML string if available
    // For now, we'll just show an empty textarea
    // In a real implementation, you'd convert the config back to TOML
    configText = "";
  });

  function handleSave() {
    if (configText.trim()) {
      onSave(configText);
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
      <textarea
        bind:value={configText}
        class="config-textarea"
        placeholder="Paste TOML config here..."
        rows="20"
      ></textarea>
    </div>
    <div class="modal-footer">
      <button class="button button-secondary" onclick={onCancel}>Cancel</button>
      <button class="button button-primary" onclick={handleSave} disabled={!configText.trim()}>
        Save
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
    width: 800px;
    display: flex;
    flex-direction: column;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
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
    flex: 1;
    overflow-y: auto;
    margin-bottom: 1rem;
  }

  .config-textarea {
    width: 100%;
    min-height: 400px;
    font-family: monospace;
    font-size: 0.875rem;
    padding: 0.75rem;
    border: 1px solid #d1d5db;
    border-radius: 0.375rem;
    resize: vertical;
    box-sizing: border-box;
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
