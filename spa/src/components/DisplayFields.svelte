<script lang="ts">
  import { DISPLAY_FIELDS, type DisplayDraft } from "../utils/config-pages.js";

  /** The fields of one display table. The owner keeps the draft. */
  let { draft }: { draft: DisplayDraft } = $props();
</script>

<div class="display-fields">
  {#each DISPLAY_FIELDS as field (field.key)}
    <label class="display-field">
      <span class="display-field-label">{field.label}</span>
      {#if field.kind === "boolean"}
        <input
          type="checkbox"
          checked={draft[field.key] === "true"}
          aria-label={field.label}
          onchange={(event) =>
            (draft[field.key] = event.currentTarget.checked ? "true" : "false")}
        />
      {:else if field.kind === "select"}
        <select bind:value={draft[field.key]} aria-label={field.label}>
          <option value="">(not set)</option>
          {#each field.options ?? [] as option (option)}
            <option value={option}>{option}</option>
          {/each}
        </select>
      {:else}
        <input
          type="number"
          bind:value={draft[field.key]}
          aria-label={field.label}
        />
      {/if}
      {#if field.hint}
        <small class="display-field-hint">{field.hint}</small>
      {/if}
    </label>
  {/each}
</div>

<style>
  .display-fields {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
    gap: 0.5rem 0.75rem;
  }

  .display-field {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    font-size: 0.8rem;
    min-width: 0;
  }

  .display-field-label {
    font-weight: 500;
  }

  .display-field input[type="number"],
  .display-field select {
    padding: 0.3rem 0.45rem;
    border: 1px solid #d1d5db;
    border-radius: 0.375rem;
    font-size: 0.85rem;
    width: 100%;
    box-sizing: border-box;
  }

  .display-field input[type="checkbox"] {
    width: 1.1rem;
    height: 1.1rem;
  }

  :global([data-theme="dark"]) .display-field input[type="number"],
  :global([data-theme="dark"]) .display-field select {
    background: #111827;
    border-color: #4b5563;
    color: #e5e7eb;
  }

  .display-field-hint {
    color: #6b7280;
    font-size: 0.72rem;
  }

  :global([data-theme="dark"]) .display-field-hint {
    color: #9ca3af;
  }
</style>
