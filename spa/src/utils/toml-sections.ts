/**
 * Just enough TOML text handling to add and remove whole tables while keeping
 * the author's comments and layout: a configuration is read as a list of
 * tables, each with the lines that belong to it.
 */

const HEADER_PATTERN = /^\s*\[\[?([^\]]+)\]\]?\s*(?:#.*)?$/;

export interface TomlTable {
  /** Table name without brackets, e.g. "routes.stops". */
  name: string;
  headerLine: number;
  /** Index just past the last line that belongs to the table. */
  endLine: number;
}

/** The table name a line opens, or `undefined` when it is not a header line. */
export function tomlTableName(line: string): string | undefined {
  return HEADER_PATTERN.exec(line)?.[1].trim();
}

/** True for the table itself and for its sub-tables: "routes", "routes.stops". */
export function belongsTo(name: string, root: string): boolean {
  return name === root || name.startsWith(`${root}.`);
}

/**
 * Splits a file into its tables. Everything before the first header is not a
 * table and is left alone by callers.
 */
export function readTomlTables(lines: string[]): TomlTable[] {
  const tables: TomlTable[] = [];

  lines.forEach((line, index) => {
    const name = tomlTableName(line);
    if (name === undefined) {
      return;
    }
    if (tables.length > 0) {
      tables[tables.length - 1].endLine = index;
    }
    tables.push({ name, headerLine: index, endLine: lines.length });
  });

  return tables;
}

/** Start of the comment block that sits directly above `line`. */
export function leadInStart(lines: string[], line: number): number {
  let start = line;
  while (start > 0 && lines[start - 1].trim().startsWith("#")) {
    start -= 1;
  }
  return start;
}

/**
 * Index just past the table's own last line: blank lines and the comment block
 * that introduces the next table stay with that table.
 */
export function tableLinesEnd(lines: string[], table: TomlTable): number {
  const firstBodyLine = table.headerLine + 1;
  let end = table.endLine;

  while (end > firstBodyLine && lines[end - 1].trim().startsWith("#")) {
    end -= 1;
  }
  while (end > firstBodyLine && lines[end - 1].trim() === "") {
    end -= 1;
  }

  return end;
}

/**
 * Renders a file with `removed` lines dropped and `inserted` lines added before
 * the line they are keyed at, collapsing runs of blank lines into one.
 */
export function renderToml(
  lines: string[],
  removed: ReadonlySet<number>,
  inserted: ReadonlyMap<number, string[]>,
): string {
  const output: string[] = [];

  for (let line = 0; line < lines.length; line += 1) {
    output.push(...(inserted.get(line) ?? []));
    if (!removed.has(line)) {
      output.push(lines[line]);
    }
  }
  output.push(...(inserted.get(lines.length) ?? []));

  return withSingleBlankLines(output).join("\n");
}

function withSingleBlankLines(lines: string[]): string[] {
  const result: string[] = [];

  for (const line of lines) {
    const blank = line.trim() === "";
    if (!blank) {
      result.push(line);
      continue;
    }
    if (result.length === 0 || result[result.length - 1].trim() === "") {
      continue;
    }
    result.push("");
  }

  while (result.length > 0 && result[result.length - 1].trim() === "") {
    result.pop();
  }

  return result;
}

/** A table's lines: its header, and the index just past its own lines. */
export interface TomlRange {
  header: number;
  /** Index just past the table's own lines. */
  end: number;
}

/** The line of `key` inside the range, or -1. */
export function tomlKeyLine(
  lines: string[],
  range: TomlRange,
  key: string,
): number {
  const pattern = new RegExp(`^\\s*${key}\\s*=`);

  for (let line = range.header + 1; line < range.end; line += 1) {
    if (pattern.test(lines[line])) {
      return line;
    }
  }

  return -1;
}

/** True when the range still holds anything but comments and `exceptKey`. */
export function tomlTableHasKeys(
  lines: string[],
  range: TomlRange,
  exceptKey?: string,
): boolean {
  const skip = exceptKey ? new RegExp(`^\\s*${exceptKey}\\s*=`) : null;

  return lines.slice(range.header + 1, range.end).some((line) => {
    const trimmed = line.trim();
    return trimmed !== "" && !trimmed.startsWith("#") && !skip?.test(line);
  });
}

/** Replaces, adds or (for `null`) removes one `key = value` line. */
export function setTomlKey(
  lines: string[],
  range: TomlRange,
  key: string,
  value: string | null,
): string[] {
  const line = tomlKeyLine(lines, range, key);
  const replacement = value === null ? null : `${key} = ${value}`;

  if (line === -1) {
    return replacement === null
      ? lines
      : [
          ...lines.slice(0, range.header + 1),
          replacement,
          ...lines.slice(range.header + 1),
        ];
  }
  if (replacement === null) {
    return [...lines.slice(0, line), ...lines.slice(line + 1)];
  }

  return lines.map((existing, index) =>
    index === line ? replacement : existing,
  );
}

/** A TOML string literal, quotes and backslashes escaped. */
export function tomlString(value: string): string {
  return `"${value.replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"`;
}
