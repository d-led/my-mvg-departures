<script lang="ts">
  import type { ConfigPage } from "../utils/config-pages.js";

  let {
    pages,
    onReorder,
    onRemovePage,
    onRemoveStop,
    onAddStops,
  }: {
    pages: ConfigPage[];
    onReorder: (from: number, to: number) => void;
    onRemovePage: (index: number) => void;
    onRemoveStop: (pageIndex: number, stopIndex: number) => void;
    onAddStops: () => void;
  } = $props();

  /** The page whose deletion is being confirmed, if any. */
  let confirmingPage = $state<number | null>(null);
  /** "pageIndex:stopIndex" of the stop whose deletion is being confirmed. */
  let confirmingStop = $state<string | null>(null);
  let draggedPage = $state<number | null>(null);

  function stopKey(pageIndex: number, stopIndex: number): string {
    return `${pageIndex}:${stopIndex}`;
  }

  function dropOn(index: number) {
    if (draggedPage !== null && draggedPage !== index) {
      onReorder(draggedPage, index);
    }
    draggedPage = null;
  }
</script>

<div class="pages">
  {#each pages as page, index (index)}
    <article
      class="page-card"
      class:is-dragged={draggedPage === index}
      draggable="true"
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
            onclick={() => (confirmingPage = index)}
          >
            Delete page
          </button>
        </div>
      </header>

      <ul class="page-stops">
        {#each page.stops as stop, stopIndex (stop.stationId)}
          <li class="page-stop">
            <span class="page-stop-name">{stop.name}</span>
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
    <p class="pages-empty">This config has no pages yet.</p>
  {/if}

  <button class="button button-secondary add-stops" onclick={onAddStops}>Add stops…</button>
</div>

<style>
  .pages {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    overflow-y: auto;
    flex: 1 1 auto;
    min-height: 0;
    padding-right: 0.25rem;
  }

  .page-card {
    border: 1px solid #e5e7eb;
    border-radius: 0.5rem;
    padding: 0.5rem 0.75rem;
    background: #f9fafb;
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

  .icon-button {
    min-width: 1.75rem;
    padding: 0.125rem 0.375rem;
  }

  .button-danger {
    background-color: #dc2626;
    color: white;
  }
</style>
