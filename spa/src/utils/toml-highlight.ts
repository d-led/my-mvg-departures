/**
 * TOML highlighting for the configuration editor. highlight.js' `ini` grammar
 * reads TOML well (sections, keys, strings, numbers, comments); only that grammar
 * is bundled, not the whole library.
 */
import hljs from "highlight.js/lib/core";
import ini from "highlight.js/lib/languages/ini";

hljs.registerLanguage("toml", ini);

/** The TOML as HTML spans, ready for the editor's highlighted layer. */
export function highlightToml(toml: string): string {
  return hljs.highlight(toml, { language: "toml" }).value;
}
