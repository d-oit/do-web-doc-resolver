export interface ApiKeys {
  serper_api_key?: string;
  tavily_api_key?: string;
  exa_api_key?: string;
  firecrawl_api_key?: string;
  mistral_api_key?: string;
}

let inMemoryKeys: ApiKeys = {};

export function loadApiKeys(): ApiKeys {
  return { ...inMemoryKeys };
}

export function saveApiKeys(keys: ApiKeys): void {
  inMemoryKeys = { ...keys };
}

export type KeySource = "local" | "server" | "free" | "none";

export function resolveKeySource(
  localKeys: ApiKeys,
  serverStatus: Record<string, boolean>
): Record<string, KeySource> {
  const hasKey = (key: string | undefined) => !!(key && key.trim());
  return {
    serper: hasKey(localKeys.serper_api_key) ? "local" : serverStatus.serper ? "server" : "none",
    tavily: hasKey(localKeys.tavily_api_key) ? "local" : serverStatus.tavily ? "server" : "none",
    exa: hasKey(localKeys.exa_api_key) ? "local" : serverStatus.exa ? "server" : "none",
    firecrawl: hasKey(localKeys.firecrawl_api_key) ? "local" : serverStatus.firecrawl ? "server" : "none",
    mistral: hasKey(localKeys.mistral_api_key) ? "local" : serverStatus.mistral ? "server" : "none",
    exa_mcp: "free",
    duckduckgo: "free",
  };
}
