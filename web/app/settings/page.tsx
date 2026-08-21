"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { loadApiKeys, saveApiKeys, ApiKeys } from "@/lib/keys";
import { loadUIState, saveUIState } from "@/lib/ui-state";

const KEY_FIELDS = [
  {
    key: "serper_api_key" as keyof ApiKeys,
    label: "Serper",
    provider: "serper",
  },
  {
    key: "tavily_api_key" as keyof ApiKeys,
    label: "Tavily",
    provider: "tavily",
  },
  {
    key: "exa_api_key" as keyof ApiKeys,
    label: "Exa",
    provider: "exa",
  },
  {
    key: "firecrawl_api_key" as keyof ApiKeys,
    label: "Firecrawl",
    provider: "firecrawl",
  },
  {
    key: "mistral_api_key" as keyof ApiKeys,
    label: "Mistral",
    provider: "mistral",
  },
];

type KeyStatus = Record<string, boolean>;

export default function SettingsPage() {
  const [apiKeys, setApiKeys] = useState<ApiKeys>(() => {
    if (typeof window === "undefined") return {};
    return loadApiKeys();
  });
  const [keyStatus, setKeyStatus] = useState<KeyStatus>({});
  const [saved, setSaved] = useState(false);
  const [visibleKeys, setVisibleKeys] = useState<Record<string, boolean>>({});

  useEffect(() => {
    fetch("/api/key-status")
      .then((res) => res.json())
      .then(setKeyStatus)
      .catch(() => {});

    loadUIState()
      .then((state) => {
        if (state?.apiKeys && Object.keys(state.apiKeys).length > 0) {
          setApiKeys(state.apiKeys);
          saveApiKeys(state.apiKeys);
        }
      })
      .catch(() => {});
  }, []);

  const persistKeys = (newKeys: ApiKeys) => {
    saveApiKeys(newKeys);
    saveUIState({ apiKeys: newKeys });
  };

  const handleKeyChange = (key: keyof ApiKeys, value: string) => {
    const newKeys = { ...apiKeys, [key]: value || undefined };
    setApiKeys(newKeys);
    persistKeys(newKeys);
    setSaved(true);
    setTimeout(() => setSaved(false), 1000);
  };

  const clearKey = (key: keyof ApiKeys) => {
    const newKeys = { ...apiKeys };
    delete newKeys[key];
    setApiKeys(newKeys);
    persistKeys(newKeys);
  };

  const toggleKeyVisibility = (key: string) => {
    setVisibleKeys((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <main className="min-h-screen bg-background text-foreground font-mono p-8">
      <div className="max-w-xl">
        <div className="mb-8">
          <Link href="/" className="text-[11px] uppercase tracking-[0.1em] text-text-muted hover:text-accent focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2">
            ← Back
          </Link>
        </div>

        <h1 className="text-[24px] font-bold tracking-tight mb-2">Settings</h1>
        <p className="text-[11px] text-text-muted mb-8">
          Configure API keys. Persisted via server-backed UI state on Vercel.
        </p>

        <div className="flex flex-col gap-4">
          {KEY_FIELDS.map((field) => {
            const value = apiKeys[field.key] || "";
            const localHasKey = !!value;
            const serverHasKey = !!keyStatus[field.provider];
            const isVisible = !!visibleKeys[field.key];

            return (
              <div key={field.key} className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <label htmlFor={`input-${field.key}`} className="text-[13px]">{field.label}</label>
                  <div className="flex items-center gap-2">
                    {localHasKey ? (
                      <span className="text-[11px] text-accent">Local key</span>
                    ) : serverHasKey ? (
                      <span className="text-[11px] text-text-muted">Server key</span>
                    ) : (
                      <span className="text-[11px] text-text-dim">Not configured</span>
                    )}
                    {localHasKey && (
                      <button
                        onClick={() => clearKey(field.key)}
                        className="text-[11px] text-[#ff4444] hover:text-[#ff6666] focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                </div>
                <div className="relative flex items-center">
                  <input
                    id={`input-${field.key}`}
                    type={isVisible ? "text" : "password"}
                    value={value}
                    onChange={(e) => handleKeyChange(field.key, e.target.value)}
                    placeholder="sk-..."
                    className="w-full bg-[#141414] border-2 border-border-muted pl-3 pr-12 py-2 text-[13px] text-foreground placeholder:text-text-dim focus:border-accent focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2"
                  />
                  {localHasKey && (
                    <button
                      type="button"
                      onClick={() => toggleKeyVisibility(field.key)}
                      className="absolute right-2 px-2 py-1 text-[11px] text-text-muted hover:text-accent focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2"
                      aria-label={isVisible ? "Hide key" : "Show key"}
                    >
                      {isVisible ? "Hide" : "Show"}
                    </button>
                  )}
                </div>
                {serverHasKey && !localHasKey && (
                  <p className="text-[11px] text-text-muted">
                    Server key available. Enter your own to override.
                  </p>
                )}
              </div>
            );
          })}
        </div>

        <div className="mt-8 p-4 border-2 border-border-muted">
          <div className="text-[11px] uppercase tracking-[0.1em] text-text-muted mb-2">
            Free providers
          </div>
          <p className="text-[11px] text-text-dim">
            Jina, Exa MCP, and DuckDuckGo are free and always available—no API key required.
          </p>
        </div>

        {saved && (
          <div className="fixed bottom-4 right-4 bg-accent text-background px-4 py-2 text-[12px] font-bold">
            Saved
          </div>
        )}
      </div>
    </main>
  );
}
