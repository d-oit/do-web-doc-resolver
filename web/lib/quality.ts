export interface QualityScore {
  score: number;
  tooShort: boolean;
  missingLinks: boolean;
  duplicateHeavy: boolean;
  noisy: boolean;
  acceptable: boolean;
}

const NOISY_SIGNALS = ["cookie", "subscribe", "javascript", "log in", "sign up"];

// Markdown inline links plus bare autolinks. These patterns mirror
// `extract_links` in scripts/quality.py so the web and Python runtimes agree
// on what counts as a link; changing one without the other skews the accept
// threshold in only half the runtimes.
const MARKDOWN_LINK_RE = /\[[^\]]*\]\(\s*<?[^)\s]+>?\s*\)/g;
const AUTOLINK_RE = /<https?:\/\/[^>\s]+>/g;

export function extractLinks(markdown: string): string[] {
  if (typeof markdown !== "string" || markdown.length === 0) {
    return [];
  }
  return [
    ...(markdown.match(MARKDOWN_LINK_RE) ?? []),
    ...(markdown.match(AUTOLINK_RE) ?? []),
  ];
}

export function scoreContent(markdown: string, links?: string[]): QualityScore {
  const text = (markdown ?? "").trim();

  // Callers score raw provider output and pass no link list, so infer the
  // links from the markdown itself. Without this `missingLinks` was always
  // true and every web result took a flat -0.10 penalty. An explicitly empty
  // `links` array still means "no links" and keeps the penalty.
  const linkCount = (links ?? extractLinks(text)).length;

  const tooShort = text.length < 500;
  const missingLinks = linkCount === 0;

  const lines = text.split("\n");
  const numLines = lines.length;
  let duplicateHeavy = false;
  if (numLines > 0) {
    const uniqueLines = new Set(lines.map((l) => l.trim()).filter(Boolean)).size;
    // Updated threshold to max(5, numLines / 3) to match Python/Rust 2026 standards
    duplicateHeavy = uniqueLines < Math.max(5, Math.floor(numLines / 3));
  }

  const lowerText = text.toLowerCase();
  const noiseCount = NOISY_SIGNALS.reduce((n, sig) => n + (lowerText.includes(sig) ? 1 : 0), 0);
  const noisy = noiseCount > 6;

  // 2026 Standard Checks
  const requiredYaml = ["relevance_score:", "intent_category:", "token_estimate:", "last_updated:"];
  const hasFrontmatter =
    text.startsWith("---") && requiredYaml.every((field) => text.includes(field));
  const hasAnchors = [
    "[ANCHOR: SUMMARY]",
    "[ANCHOR: TECHNICAL_DETAILS]",
    "[ANCHOR: COMPARISON]",
    "[ANCHOR: CITATIONS]",
  ].every((anchor) => text.includes(anchor));

  // Penalties updated to match 2026 standards
  let score = 1.0;
  if (tooShort) score -= 0.25;
  if (missingLinks) score -= 0.1;
  if (duplicateHeavy) score -= 0.15;
  if (noisy) score -= 0.1;

  // Bonuses for 2026 standards
  if (hasFrontmatter) score += 0.05;
  if (hasAnchors) score += 0.05;

  score = Math.max(0, Math.min(1.0, score));

  // Threshold for acceptance: 0.65 and not tooShort
  const acceptable = score >= 0.65 && !tooShort;

  return { score, tooShort, missingLinks, duplicateHeavy, noisy, acceptable };
}
