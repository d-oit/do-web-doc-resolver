import type { ApiKeys } from "./keys";

/**
 * Persisted UI preferences.
 *
 * Deliberately excludes API keys. `UIState` is written to localStorage in
 * clear text and synced to `/api/ui-state`, so keeping credentials in it would
 * store secrets at rest. Keys live only in `keys.ts` (in-memory, per session).
 */
export interface UIState {
  sidebarCollapsed: boolean;
  showApiKeys: boolean;
  showAdvanced: boolean;
  activeProfile: string;
  theme: "light" | "dark";
  selectedProviders: string[];
  maxChars: number;
  skipCache: boolean;
  deepResearch: boolean;
  lastUpdated: number;
}

const STORAGE_KEY = "wdr-ui-state";

// Default state values
const DEFAULTS: UIState = {
  sidebarCollapsed: false,
  showApiKeys: false,
  showAdvanced: false,
  activeProfile: "free",
  theme: "dark",
  selectedProviders: [],
  maxChars: 8000,
  skipCache: false,
  deepResearch: false,
  lastUpdated: 0,
};

// Normalize partial state to full UIState
function normalizeUIState(value: unknown): UIState {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return DEFAULTS;
  }

  const parsed = value as Partial<UIState>;

  // Normalize selectedProviders to string array
  const selectedProviders = Array.isArray(parsed.selectedProviders)
    ? parsed.selectedProviders.filter((p): p is string => typeof p === "string")
    : DEFAULTS.selectedProviders;

  // Normalize theme to valid values
  const theme = parsed.theme === "light" || parsed.theme === "dark" 
    ? parsed.theme 
    : DEFAULTS.theme;

  // Normalize activeProfile
  const activeProfile = typeof parsed.activeProfile === "string" 
    ? parsed.activeProfile 
    : DEFAULTS.activeProfile;

  return {
    sidebarCollapsed: typeof parsed.sidebarCollapsed === "boolean" 
      ? parsed.sidebarCollapsed 
      : DEFAULTS.sidebarCollapsed,
    showApiKeys: typeof parsed.showApiKeys === "boolean" 
      ? parsed.showApiKeys 
      : DEFAULTS.showApiKeys,
    showAdvanced: typeof parsed.showAdvanced === "boolean" 
      ? parsed.showAdvanced 
      : DEFAULTS.showAdvanced,
    activeProfile,
    theme,
    selectedProviders,
    maxChars: typeof parsed.maxChars === "number" ? parsed.maxChars : DEFAULTS.maxChars,
    skipCache: typeof parsed.skipCache === "boolean" ? parsed.skipCache : DEFAULTS.skipCache,
    deepResearch:
      typeof parsed.deepResearch === "boolean" ? parsed.deepResearch : DEFAULTS.deepResearch,
    lastUpdated: typeof parsed.lastUpdated === "number" ? parsed.lastUpdated : DEFAULTS.lastUpdated,
  };
}

// Merge server and local state (server wins on conflict)
export function resolveUIState(serverState: UIState | null, localState: UIState): UIState {
  if (!serverState) return localState;

  // Server wins for conflicts (newer timestamp takes precedence)
  if (serverState.lastUpdated >= localState.lastUpdated) {
    return serverState;
  }

  return localState;
}



// Load from localStorage (for server-side rendering safety)
function loadFromLocalStorage(): UIState {
  if (typeof window === "undefined") return DEFAULTS;
  
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return DEFAULTS;
    return normalizeUIState(JSON.parse(stored));
  } catch {
    return DEFAULTS;
  }
}

/**
 * Project onto the persistable field set.
 *
 * Fields are copied explicitly rather than spread, so no value can reach
 * storage by accident — including credentials passed by a JS caller or
 * carried in a stale localStorage blob from an older build.
 */
function toPersistable(state: Partial<UIState>): Partial<UIState> {
  const out: Partial<UIState> = {};
  if (typeof state.sidebarCollapsed === "boolean") out.sidebarCollapsed = state.sidebarCollapsed;
  if (typeof state.showApiKeys === "boolean") out.showApiKeys = state.showApiKeys;
  if (typeof state.showAdvanced === "boolean") out.showAdvanced = state.showAdvanced;
  if (typeof state.activeProfile === "string") out.activeProfile = state.activeProfile;
  if (state.theme === "light" || state.theme === "dark") out.theme = state.theme;
  if (Array.isArray(state.selectedProviders)) out.selectedProviders = state.selectedProviders;
  if (typeof state.maxChars === "number") out.maxChars = state.maxChars;
  if (typeof state.skipCache === "boolean") out.skipCache = state.skipCache;
  if (typeof state.deepResearch === "boolean") out.deepResearch = state.deepResearch;
  if (typeof state.lastUpdated === "number") out.lastUpdated = state.lastUpdated;
  return out;
}

// Save to localStorage immediately (optimistic update)
function saveToLocalStorage(state: Partial<UIState>): void {
  if (typeof window === "undefined") return;

  try {
    const current = loadFromLocalStorage();
    const next = normalizeUIState({
      ...toPersistable(current),
      ...toPersistable(state),
      lastUpdated: Date.now(),
    });
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    // Ignore storage errors (private mode, quota exceeded)
  }
}

// Load UI state from server with localStorage fallback
export async function loadUIState(): Promise<UIState> {
  // Always load local first for immediate feedback
  const localState = loadFromLocalStorage();
  
  try {
    const res = await fetch("/api/ui-state");
    if (!res.ok) return localState;
    
    const serverData = await res.json();
    const serverState = normalizeUIState(serverData);
    
    // Merge: server wins for conflicts
    const merged = resolveUIState(
      Object.keys(serverData).length > 0 ? serverState : null,
      localState
    );
    
    // Deliberately not writing `merged` back to localStorage here. The result
    // is applied to React state, and the mount effect in page.tsx then persists
    // it via saveUIState, which already projects through toPersistable(). Writing
    // it at this point would duplicate that with a value that traces back to the
    // untrusted server response.
    return merged;
  } catch {
    // Offline or server error: use localStorage
    return localState;
  }
}

// Save UI state to localStorage + background sync to server
export function saveUIState(state: Partial<UIState>): void {
  // Immediate localStorage update for responsiveness
  saveToLocalStorage(state);
  
  // Fire-and-forget background sync to server
  // Don't await - this shouldn't block the UI
  syncToServer(state).catch(() => {
    // Silently fail - localStorage is the source of truth
  });
}

// Background sync to server
async function syncToServer(state: Partial<UIState>): Promise<void> {
  try {
    const current = loadFromLocalStorage();
    const payload = normalizeUIState({
      ...toPersistable(current),
      ...toPersistable(state),
      lastUpdated: Date.now(),
    });

    const res = await fetch("/api/ui-state", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    
    if (!res.ok) {
      throw new Error(`Server returned ${res.status}`);
    }
  } catch {
    // Server unavailable - state is saved in localStorage
    // Will sync on next save or page load
  }
}

// Legacy exports for backward compatibility (deprecated)
export async function loadStateFromServer(): Promise<UIState | null> {
  try {
    const res = await fetch("/api/ui-state");
    if (!res.ok) return null;
    const data = await res.json();
    return normalizeUIState(data);
  } catch {
    return null;
  }
}

export async function saveStateToServer(state: Partial<UIState>): Promise<void> {
  return syncToServer(state);
}

// Re-export types for convenience
export type { ApiKeys };
