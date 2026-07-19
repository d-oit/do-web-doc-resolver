"use client";

import { MainHeader } from "@/app/components/MainHeader";
import { SearchSection } from "@/app/components/SearchSection";
import { MetadataBar } from "@/app/components/MetadataBar";
import ResultCard from "@/app/components/ResultCard";
import type { ProviderResult } from "@/lib/results";

interface MainContentProps {
  mobileMenuOpen: boolean;
  setMobileMenuOpen(open: boolean): void;
  query: string;
  setQuery(query: string): void;
  handleSubmit(e?: React.FormEvent): void;
  loading: boolean;
  inputRef: React.RefObject<HTMLInputElement | null>;
  error: string;
  result: string;
  setResult(result: string): void;
  setError(error: string): void;
  providerStatus: string | null;
  setProviderStatus(status: string | null): void;
  sourceProvider: string | null;
  setSourceProvider(provider: string | null): void;
  resolveTime: number | null;
  setResolveTime(time: number | null): void;
  qualityScore: number | null;
  setQualityScore(score: number | null): void;
  parsedResults: ProviderResult[];
  setParsedResults(results: ProviderResult[]): void;
  viewRaw: boolean;
  setViewRaw(view: boolean): void;
  helpfulIds: Set<string>;
  toggleHelpful(id: string): void;
  handleCopyResult(): void;
  handleCardCopy(value: string): void;
  copied: boolean;
  isUrl: boolean;
  onShowShortcuts: () => void;
}

export function MainContent(props: MainContentProps) {
  const {
    mobileMenuOpen,
    setMobileMenuOpen,
    query,
    setQuery,
    handleSubmit,
    loading,
    inputRef,
    error,
    result,
    setResult,
    setError,
    providerStatus,
    setProviderStatus,
    sourceProvider,
    setSourceProvider,
    resolveTime,
    setResolveTime,
    qualityScore,
    setQualityScore,
    parsedResults,
    setParsedResults,
    viewRaw,
    setViewRaw,
    helpfulIds,
    toggleHelpful,
    handleCopyResult,
    handleCardCopy,
    copied,
    isUrl,
    onShowShortcuts,
  } = props;

  function handleClear() {
    setQuery("");
    setResult("");
    setError("");
    setProviderStatus(null);
    setResolveTime(null);
    setSourceProvider(null);
    setQualityScore(null);
    setParsedResults([]);
    setViewRaw(false);
    inputRef.current?.focus();
  }

  return (
    <div id="main-content" className="flex-1 flex flex-col min-h-0" tabIndex={-1}>
      <MainHeader setMobileMenuOpen={setMobileMenuOpen} mobileMenuOpen={mobileMenuOpen} onShowShortcuts={onShowShortcuts} />

      <SearchSection
        query={query}
        setQuery={setQuery}
        handleSubmit={handleSubmit}
        loading={loading}
        inputRef={inputRef}
        error={error}
        hasResult={Boolean(result)}
        onClear={handleClear}
        providerStatus={providerStatus}
        isUrl={isUrl}
      />

      {error && (
        <div id="search-error" role="alert" className="p-4 border-b-2 border-border-muted text-error text-[13px]">
          {error}
        </div>
      )}

      <div className="flex-1 flex flex-col min-h-0">
        {result ? (
          <>
            <MetadataBar
              sourceProvider={sourceProvider}
              resolveTime={resolveTime}
              charCount={result.length}
              qualityScore={qualityScore}
              viewRaw={viewRaw}
              setViewRaw={setViewRaw}
              handleCopyResult={handleCopyResult}
              copied={copied}
            />
            {viewRaw || parsedResults.length === 0 ? (
              <textarea
                readOnly
                value={result}
                className="flex-1 bg-[#141414] p-4 text-[13px] text-foreground font-mono resize-none whitespace-pre-wrap overflow-auto min-h-[200px]"
              />
            ) : (
              <div className="flex-1 overflow-auto bg-background p-4 space-y-4">
                {parsedResults.map((parsed) => (
                  <ResultCard
                    key={parsed.id}
                    result={parsed}
                    onCopy={handleCardCopy}
                    onHelpfulToggle={toggleHelpful}
                    helpful={helpfulIds.has(parsed.id)}
                  />
                ))}
              </div>
            )}
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-text-dim text-[13px] p-4 text-center">
            Paste a URL or enter a search query
          </div>
        )}
      </div>
    </div>
  );
}

export default MainContent;
