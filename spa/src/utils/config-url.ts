export function readConfigUrlParam(search: string): string | null {
  const params = new globalThis.URLSearchParams(search);
  const rawValue = params.get("config");
  if (!rawValue) {
    return null;
  }

  const trimmed = rawValue.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export function normalizeConfigUrl(rawUrl: string): string | null {
  try {
    const parsed = new URL(rawUrl);
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
      return null;
    }
    return parsed.href;
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
    throw new Error("Invalid config URL. Only absolute http(s) URLs are supported.");
  }

  const response = await fetchImpl(configUrl);
  if (!response.ok) {
    throw new Error(
      `Failed to fetch config from URL: ${response.status} ${response.statusText}`,
    );
  }

  const toml = await response.text();
  if (!toml.trim()) {
    throw new Error("Config URL returned an empty response.");
  }

  return { configUrl, toml };
}
