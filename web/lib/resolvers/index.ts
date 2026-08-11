import { Logger } from "@/lib/log";
import {
  extractViaLlmsTxt,
  extractViaJina,
  extractViaDirectFetch,
  extractViaFirecrawl,
  extractViaMistralBrowser,
} from "./url";
import {
  searchViaExaMcp,
  searchViaExaSdk,
  searchViaSerper,
  searchViaTavily,
  searchViaDuckDuckGoLite,
  searchViaDuckDuckGoFree,
  searchViaMistralWeb,
} from "./query";

export type ProviderFn = (
  query: string,
  keys: ProviderKeys,
  log: Logger,
  maxChars?: number
) => Promise<string | null>;

export interface ProviderKeys {
  SERPER_API_KEY?: string;
  TAVILY_API_KEY?: string;
  EXA_API_KEY?: string;
  FIRECRAWL_API_KEY?: string;
  MISTRAL_API_KEY?: string;
}

export function isUrl(input: string): boolean {
  return /^https?:\/\/\S+$/i.test(input.trim());
}

export const queryProviders: Record<string, ProviderFn> = {
  exa_mcp: async (q, _k, log, maxChars) => searchViaExaMcp(q, log, maxChars),
  exa: async (q, k, log, maxChars) => searchViaExaSdk(q, k.EXA_API_KEY || "", log, maxChars),
  serper: async (q, k, log, maxChars) => searchViaSerper(q, k.SERPER_API_KEY || "", log, maxChars),
  tavily: async (q, k, log, maxChars) => searchViaTavily(q, k.TAVILY_API_KEY || "", log, maxChars),
  duckduckgo: async (q, _k, log, maxChars) =>
    (await searchViaDuckDuckGoLite(q, log, maxChars)) || (await searchViaDuckDuckGoFree(q, log, maxChars)),
  mistral_websearch: async (q, k, log, maxChars) =>
    searchViaMistralWeb(q, k.MISTRAL_API_KEY || "", log, maxChars),
};

export const urlProviders: Record<string, ProviderFn> = {
  llms_txt: async (q, _k, log, maxChars) => extractViaLlmsTxt(q, log, maxChars),
  jina: async (q, _k, log, maxChars) => extractViaJina(q, log, maxChars),
  firecrawl: async (q, k, log, maxChars) => extractViaFirecrawl(q, k.FIRECRAWL_API_KEY || "", log, maxChars),
  direct_fetch: async (q, _k, log, maxChars) => extractViaDirectFetch(q, log, maxChars),
  mistral_browser: async (q, k, log, maxChars) =>
    extractViaMistralBrowser(q, k.MISTRAL_API_KEY || "", log, maxChars),
};

export const paidProviders = new Set(["exa", "serper", "tavily", "firecrawl", "mistral_websearch", "mistral_browser"]);
