"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

// API key configuration stored in localStorage
interface ApiKeys {
  serper_api_key?: string;
  tavily_api_key?: string;
  exa_api_key?: string;
  firecrawl_api_key?: string;
  mistral_api_key?: string;
}

const STORAGE_KEY = "web-resolver-api-keys";

function loadApiKeys(): ApiKeys {
  if (typeof window === "undefined") return {};
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : {};
  } catch {
    return {};
  }
}

function saveApiKeys(keys: ApiKeys): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(keys));
  } catch {
    // Ignore storage errors
  }
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showSettings, setShowSettings] = useState(false);
  const [apiKeys, setApiKeys] = useState<ApiKeys>({});

  // Load API keys on mount
  useEffect(() => {
    setApiKeys(loadApiKeys());
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError("");
    setResult("");

    try {
      const res = await fetch("/api/resolve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: query.trim(),
          // Include user-provided API keys if available
          ...apiKeys,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || `Resolver returned ${res.status}`);
      }

      setResult(data.markdown || data.result || JSON.stringify(data, null, 2));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to resolve query"
      );
    } finally {
      setLoading(false);
    }
  };

  const handleKeyChange = (key: keyof ApiKeys, value: string) => {
    const newKeys = { ...apiKeys, [key]: value || undefined };
    setApiKeys(newKeys);
    saveApiKeys(newKeys);
  };

  const clearKeys = () => {
    setApiKeys({});
    saveApiKeys({});
  };

  const hasKeys = Object.values(apiKeys).some(v => v);

  return (
    <main className="flex min-h-screen flex-col items-center p-8 sm:p-16">
      <nav className="w-full max-w-2xl flex items-center justify-between mb-8">
        <Link href="/" className="text-lg font-semibold">
          d.o. Web Doc Resolver
        </Link>
        <div className="flex gap-4 items-center">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className={`text-sm ${hasKeys ? 'text-blue-600 dark:text-blue-400' : 'text-neutral-500 dark:text-neutral-400'} hover:text-neutral-900 dark:hover:text-neutral-100`}
            title="API Keys Settings"
          >
            {hasKeys ? '🔑 Keys' : 'Settings'}
          </button>
          <Link
            href="/help"
            className="text-sm text-neutral-500 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-100"
          >
            Help
          </Link>
        </div>
      </nav>

      <div className="w-full max-w-2xl">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold tracking-tight sm:text-6xl">
            d.o. Web Doc Resolver
          </h1>
          <p className="mt-4 text-lg text-neutral-600 dark:text-neutral-400">
            Resolve queries and URLs into compact, LLM-ready markdown
          </p>
        </div>

        {/* Optional API Keys Settings */}
        {showSettings && (
          <div className="mb-6 rounded-lg border border-neutral-200 bg-neutral-50 p-4 dark:border-neutral-800 dark:bg-neutral-900">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-medium text-sm">Optional API Keys</h3>
              {hasKeys && (
                <button
                  onClick={clearKeys}
                  className="text-xs text-red-600 hover:text-red-700 dark:text-red-400"
                >
                  Clear All
                </button>
              )}
            </div>
            <p className="text-xs text-neutral-500 dark:text-neutral-400 mb-3">
              Add your own API keys for enhanced search. Keys are stored locally in your browser.
              Without keys, free DuckDuckGo search is used.
            </p>
            <div className="grid gap-2">
              {[
                { key: 'serper_api_key', label: 'Serper (Google Search)', placeholder: 'Free 2500 credits at serper.dev' },
                { key: 'tavily_api_key', label: 'Tavily', placeholder: 'tavily.com' },
                { key: 'exa_api_key', label: 'Exa', placeholder: 'exa.ai' },
              ].map(({ key, label, placeholder }) => (
                <div key={key} className="flex gap-2 items-center">
                  <label className="text-xs text-neutral-600 dark:text-neutral-400 w-32 shrink-0">
                    {label}
                  </label>
                  <input
                    type="password"
                    placeholder={placeholder}
                    value={(apiKeys as Record<string, string>)[key] || ''}
                    onChange={(e) => handleKeyChange(key as keyof ApiKeys, e.target.value)}
                    className="flex-1 rounded border border-neutral-300 bg-white px-2 py-1 text-xs dark:border-neutral-700 dark:bg-neutral-800"
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex gap-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter a URL or query..."
            className="flex-1 rounded-lg border border-neutral-300 bg-white px-4 py-3 text-neutral-900 placeholder:text-neutral-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-100 dark:placeholder:text-neutral-500"
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="rounded-lg bg-blue-600 px-6 py-3 font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Resolving..." : "Resolve"}
          </button>
        </form>

        {error && (
          <div className="mt-6 rounded-lg border border-red-300 bg-red-50 p-4 text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
            {error}
          </div>
        )}

        {result && (
          <div className="mt-6">
            <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-4 dark:border-neutral-800 dark:bg-neutral-900">
              <pre className="whitespace-pre-wrap font-mono text-sm text-neutral-800 dark:text-neutral-200">
                {result}
              </pre>
            </div>
          </div>
        )}

        <div className="mt-12 text-center text-sm text-neutral-500 dark:text-neutral-400">
          <p>
            Try a URL like{" "}
            <code className="rounded bg-neutral-100 px-1.5 py-0.5 dark:bg-neutral-800">
              https://docs.python.org
            </code>{" "}
            or a query like{" "}
            <code className="rounded bg-neutral-100 px-1.5 py-0.5 dark:bg-neutral-800">
              python async best practices
            </code>
          </p>
        </div>
      </div>
    </main>
  );
}