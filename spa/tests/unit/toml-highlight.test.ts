import { describe, expect, it } from "vitest";
import { highlightToml } from "../../src/utils/toml-highlight.js";

describe("highlightToml", () => {
  it("marks sections, keys, strings and comments", () => {
    const html = highlightToml(`[display]
title = "Zuhause" # the note
refresh_interval_seconds = 20
`);

    expect(html).toContain('class="hljs-section">[display]');
    expect(html).toContain('class="hljs-attr">title');
    expect(html).toContain("hljs-string");
    expect(html).toContain("hljs-comment");
  });

  it("marks array-of-tables headers as sections too", () => {
    expect(highlightToml('[[routes]]\npath = "/"\n')).toContain(
      'class="hljs-section"',
    );
  });

  it("escapes what the textarea would show as text", () => {
    const html = highlightToml(`note = "<b>&</b>"\n`);

    expect(html).not.toContain("<b>");
    expect(html).toContain("&lt;b&gt;");
  });
});
