"use client";

import { RefObject, FormEvent } from "react";

interface SearchSectionProps {
  query: string;
  setQuery: (query: string) => void;
  handleSubmit: (e?: FormEvent) => void;
  loading: boolean;
  inputRef: RefObject<HTMLInputElement | null>;
  error: string;
  hasResult: boolean;
  onClear: () => void;
  providerStatus: string | null;
  isUrl: boolean;
}

export const SearchSection = ({
  query,
  setQuery,
  handleSubmit,
  loading,
  inputRef,
  error,
  hasResult,
  onClear,
  providerStatus,
  isUrl,
}: SearchSectionProps) => (
  <section className="border-b-2 border-border-muted p-4">
    <div className="flex items-center gap-4">
      <label htmlFor="search-input" className="sr-only">
        URL or search query
      </label>
      <div className="flex-1 relative">
        <input
          id="search-input"
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
          placeholder="URL or search query..."
          aria-invalid={Boolean(error)}
          aria-errormessage={error ? "search-error" : undefined}
          className="w-full bg-transparent text-[20px] sm:text-[24px] text-foreground placeholder:text-text-dim tracking-tight pr-10"
        />
        {query && (
          <button
            type="button"
            onClick={() => {
              setQuery("");
              inputRef.current?.focus();
            }}
            className="absolute right-0 top-1/2 -translate-y-1/2 p-2 text-text-dim hover:text-accent transition-colors"
            aria-label="Clear query"
          >
            ×
          </button>
        )}
      </div>
      {(query.trim() || hasResult) && (
        <div className="flex items-center gap-2">
          {query.trim() && (
            <button
              onClick={() => handleSubmit()}
              disabled={loading}
              aria-label={loading ? "Fetching results..." : "Fetch results"}
              className="bg-accent text-background px-4 py-2 text-[13px] font-bold hover:bg-[#00cc33] disabled:opacity-50 min-w-[60px] min-h-[44px]"
            >
              {loading ? "..." : "Fetch"}
            </button>
          )}
          <button
            onClick={onClear}
            aria-label="Clear input and results"
            className="bg-transparent text-text-dim px-4 py-2 text-[13px] border-2 border-border-muted hover:border-accent hover:text-accent min-h-[44px]"
          >
            Clear
          </button>
        </div>
      )}
    </div>
    {query.trim() && (
      <div className="text-[11px] text-text-muted mt-2 uppercase tracking-wider">
        {isUrl ? "Resolving as URL" : "Searching"}
      </div>
    )}
    {providerStatus && (
      <div role="status" aria-live="polite" className="text-[11px] text-accent mt-2 animate-pulse">
        {providerStatus}
      </div>
    )}
  </section>
);
