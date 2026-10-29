<script lang="ts">
  import type { DisplayDraft } from "../utils/config-pages.js";
  import { displayFieldGroups } from "../utils/config-pages.js";

  /** The fields of one display table. The owner keeps the draft. */
  let { draft }: { draft: DisplayDraft } = $props();

  /** A switch and a field are read differently, so they are laid out apart. */
  const groups = displayFieldGroups().map((group) => ({
    name: group.name,
    flags: group.fields.filter((field) => field.kind === "boolean"),
    values: group.fields.filter((field) => field.kind !== "boolean"),
  }));
</script>

<!-- One section per kind of setting: switches on one line, values in short
     columns. A long file of full-width boxes is unreadable on a phone. -->
<div class="display-fields">
  {#each groups as group (group.name)}
    <section class="display-group">
      <h4>{group.name}</h4>

      {#if group.flags.length > 0}
        <div class="display-flags">
          {#each group.flags as field (field.key)}
            <label class="display-flag" title={field.hint ?? ""}>
              <input
                type="checkbox"
                checked={draft[field.key] === "true"}
                aria-label={field.label}
                onchange={(event) =>
                  (draft[field.key] = event.currentTarget.checked
                    ? "true"
                    : "false")}
              />
              <span>{field.label}</span>
            </label>
          {/each}
        </div>
      {/if}

      {#if group.values.length > 0}
        <div class="display-grid">
          {#each group.values as field (field.key)}
            <label class="display-field" title={field.hint ?? ""}>
              <span class="display-field-label">{field.label}</span>
              {#if field.kind === "select"}
                <select bind:value={draft[field.key]} aria-label={field.label}>
                  <option value="">(not set)</option>
                  {#each field.options ?? [] as option (option)}
                    <option value={option}>{option}</option>
                  {/each}
                </select>
              {:else}
                <input
                  type={field.kind === "number" ? "number" : "text"}
                  bind:value={draft[field.key]}
                  placeholder={field.fallback ?? ""}
                  aria-label={field.label}
                />
              {/if}
            </label>
          {/each}
        </div>
      {/if}
    </section>
  {/each}
</div>

<style>
  .display-fields {
    display: flex;
    flex-direction: column;
    gap: 0.9rem;
  }

  .display-group h4 {
    margin: 0 0 0.35rem;
    font-size: 0.6875rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #6b7280;
  }

  /* Switches wrap onto as many lines as they need, each one a thumb wide. */
  .display-flags {
    display: flex;
    flex-wrap: wrap;
    gap: 0 1rem;
    margin-bottom: 0.35rem;
  }

  .display-flag {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    min-height: 2.5rem;
    font-size: 0.8125rem;
    color: #111827;
  }

  .display-flag input {
    flex: 0 0 auto;
    width: 1.25rem;
    height: 1.25rem;
    accent-color: #087bc4;
  }

  /* Two columns wherever they fit, one on a narrow phone. The boxes line up at
     their bottom edge, whatever the label above them wraps to. */
  .display-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(7.5rem, 1fr));
    align-items: end;
    gap: 0.45rem 0.75rem;
  }

  .display-field {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    min-width: 0;
    font-size: 0.8125rem;
  }

  .display-field-label {
    color: #4b5563;
    line-height: 1.25;
  }

  .display-field input[type="text"],
  .display-field input[type="number"],
  .display-field select {
    width: 100%;
    min-width: 0;
    min-height: 2.5rem;
    box-sizing: border-box;
    padding: 0.3rem 0.5rem;
    border: 1px solid #d1d5db;
    border-radius: 0.375rem;
    background: #ffffff;
    color: #111827;
    font: inherit;
    font-size: 0.9375rem;
  }

  :global([data-theme="dark"]) .display-group h4 {
    color: #9ca3af;
  }

  :global([data-theme="dark"]) .display-field-label {
    color: #9ca3af;
  }

  :global([data-theme="dark"]) .display-flag {
    color: #e5e7eb;
  }

  :global([data-theme="dark"]) .display-field input[type="text"],
  :global([data-theme="dark"]) .display-field input[type="number"],
  :global([data-theme="dark"]) .display-field select {
    background: #111827;
    border-color: #4b5563;
    color: #e5e7eb;
  }
</style>
