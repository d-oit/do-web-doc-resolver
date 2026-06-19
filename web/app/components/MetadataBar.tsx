"use client";

interface MetadataBarProps {
  sourceProvider: string | null;
  resolveTime: number | null;
  charCount: number;
  qualityScore: number | null;
  viewRaw: boolean;
  setViewRaw(view: boolean): void;
  handleCopyResult(): void;
  copied: boolean;
}

export function MetadataBar({
  sourceProvider,
  resolveTime,
  charCount,
  qualityScore,
  viewRaw,
  setViewRaw,
  handleCopyResult,
  copied,
}: MetadataBarProps) {
  const handleCardsClick = () => {
    setViewRaw(false);
  }

  const handleRawClick = () => {
    setViewRaw(true);
  }

  return (
    <div className="flex items-center justify-between flex-wrap gap-3 px-4 py-2 border-b-2 border-border-muted text-[11px] text-text-muted">
      <div className="flex items-center gap-4 flex-wrap">
        <span>
          Source: <span className="text-accent">{sourceProvider}</span>
        </span>
        {resolveTime && <span>{resolveTime}ms</span>}
        <span>{charCount.toLocaleString()} chars</span>
        {qualityScore !== null && (
          <span title="Quality score (0-100)">
            Quality:{" "}
            <span
              className={
                qualityScore >= 70 ? "text-accent" : qualityScore >= 40 ? "text-[#ffaa00]" : "text-error"
              }
            >
              {qualityScore}
            </span>
          </span>
        )}
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={handleCardsClick}
          className={`px-3 py-1 border border-border-muted ${!viewRaw ? "text-accent border-accent" : "text-text-muted"}`}
          aria-pressed={!viewRaw}
          title="View results as individual structured cards"
        >
          Cards
        </button>
        <button
          onClick={handleRawClick}
          className={`px-3 py-1 border border-border-muted ${viewRaw ? "text-accent border-accent" : "text-text-muted"}`}
          aria-pressed={viewRaw}
          title="View results as raw markdown text"
        >
          Raw
        </button>
        <button
          onClick={handleCopyResult}
          aria-label={copied ? "Copied to clipboard" : "Copy to clipboard"}
          aria-live="polite"
          title="Copy full result as markdown"
          className={`transition-colors min-h-[36px] px-2 ${copied ? "text-accent" : "text-text-muted hover:text-foreground"}`}
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
    </div>
  );
}
