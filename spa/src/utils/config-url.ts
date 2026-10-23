export function readConfigUrlParam(search: string): string | null {
  const params = new globalThis.URLSearchParams(search);
  const rawValue = params.get("config");
  if (!rawValue) {
    return null;
  }

  const trimmed = rawValue.trim();
  return trimmed.length > 0 ? trimmed : null;
}

/**
 * The URL that serves a config's contents, or null when we do not know how to
 * read it. GitHub's `blob/` and gist pages are HTML, so they are translated to
 * the raw hosts; everything else is used as given.
 */
export function rawConfigUrl(url: URL): string | null {
  if (url.hostname === "github.com") {
    const [, owner, repo, kind, ...rest] = url.pathname.split("/");
    if (kind !== "blob" || !owner || !repo || rest.length < 2) {
      return null;
    }
    return `https://raw.githubusercontent.com/${owner}/${repo}/${rest.join("/")}`;
  }

  if (url.hostname === "gist.github.com") {
    const [, user, id] = url.pathname.split("/");
    if (!user || !id) {
      return null;
    }
    return `https://gist.githubusercontent.com/${user}/${id}/raw`;
  }

  return null;
}

/** Accepts any http(s) link; GitHub file pages become their raw content URLs. */
export function normalizeConfigUrl(rawUrl: string): string | null {
  try {
    const parsed = new URL(rawUrl);
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
      return null;
    }
    return rawConfigUrl(parsed) ?? parsed.href;
  } catch {
    return null;
  }
}

export async function fetchConfigTomlFromSearch(
  search: string,
  fetchImpl: typeof fetch = fetch,
): Promise<{ configUrl: string; toml: string } | null> {
  const configParam = readConfigUrlParam(search);
  if (!configParam) {
    return null;
  }

  const configUrl = normalizeConfigUrl(configParam);
  if (!configUrl) {
    throw new Error(
      "Invalid config URL. Only absolute http(s) URLs are supported.",
    );
  }

  return { configUrl, toml: await fetchToml(configUrl, fetchImpl) };
}

export async function fetchToml(
  url: string,
  fetchImpl: typeof fetch = fetch,
): Promise<string> {
  const response = await fetchImpl(url);
  if (!response.ok) {
    throw new Error(
      `Failed to fetch config from URL: ${response.status} ${response.statusText}`,
    );
  }

  const toml = await response.text();
  if (!toml.trim()) {
    throw new Error("Config URL returned an empty response.");
  }

  return toml;
}
