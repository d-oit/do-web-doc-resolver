"use client";

import { useState } from "react";
import type { ProviderResult } from "@/lib/results";

const PLACEHOLDER_REGEX = /^(n\/a|na|unknown|none|-|–)$/iu;

interface ResultCardProps {
  result: ProviderResult;
  onCopy: (value: string) => Promise<void> | void;
  onHelpfulToggle?: (id: string) => void;
  helpful?: boolean;
}

const ResultHeader = ({ id, title, url, normalizedUrl }: { id: string; title: string; url?: string | null; normalizedUrl?: string | null }) => (
  <header className="flex flex-col gap-1">
    <h3 className="text-[15px]">
      {url ? (
        <a
          id={id}
          href={url}
          target="_blank"
          rel="noreferrer"
          className="text-accent hover:underline"
        >
          {title}
        </a>
      ) : (
        <span id={id} className="text-foreground">
          {title}
        </span>
      )}
    </h3>
    {normalizedUrl && (
      <div className="text-[10px] text-text-dim break-all">{normalizedUrl}</div>
    )}
  </header>
);

const ResultMeta = ({ author, published }: { author?: string | null; published?: string | null }) => {
  const hasAuthor = author && !PLACEHOLDER_REGEX.test(author.trim());
  const hasPublished = published && !PLACEHOLDER_REGEX.test(published.trim());

  if (!hasAuthor && !hasPublished) return null;

  return (
    <div className="text-[10px] text-text-dim flex gap-3 flex-wrap">
      {hasAuthor && <span>By {author}</span>}
      {hasPublished && <span>{published}</span>}
    </div>
  );
};

export default function ResultCard({ result, onCopy, onHelpfulToggle, helpful }: ResultCardProps) {
  const [copying, setCopying] = useState(false);

  const handleCopy = async () => {
    setCopying(true);
    await onCopy(result.raw);
    setTimeout(() => setCopying(false), 1000);
  };

  return (
    <article className="border-2 border-border-muted bg-background p-4 flex flex-col gap-3" aria-labelledby={result.id ? `result-${result.id}` : undefined}
    >
      <div className="flex flex-col gap-1">
        <ResultHeader
          id={result.id ? `result-${result.id}` : ""}
          title={result.title}
          url={result.url ?? null}
          normalizedUrl={result.normalizedUrl ?? null}
        />
        <ResultMeta author={result.author ?? null} published={result.published ?? null} />
      </div>

      <p className="text-[12px] text-foreground whitespace-pre-wrap leading-relaxed">{result.snippet}</p>

      <footer className="flex flex-wrap gap-2 text-[11px]">
        <button
          onClick={handleCopy}
          className={`px-3 py-2 border-2 transition-colors ${
            copying ? "border-accent text-accent" : "border-border-muted text-text-muted hover:border-accent"
          }`}
          aria-live="polite"
          title="Copy full result as markdown"
        >
          {copying ? "Copied" : "Copy markdown"}
        </button>
        {result.url && (
          <a
            href={result.url}
            target="_blank"
            rel="noreferrer"
            className="px-3 py-2 border-2 border-border-muted hover:border-accent text-text-muted"
          >
            Open
          </a>
        )}
        {onHelpfulToggle && (
          <button
            onClick={() => onHelpfulToggle(result.id)}
            className={`px-3 py-2 border-2 ${
              helpful ? "border-accent text-accent" : "border-border-muted text-text-dim"
            }`}
            aria-pressed={helpful}
          >
            {helpful ? "Marked helpful" : "Mark helpful"}
          </button>
        )}
      </footer>
    </article>
  );
}
