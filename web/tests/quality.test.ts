import { describe, it, expect } from "vitest";
import { extractLinks, scoreContent } from "../lib/quality";

function longText(len: number = 600): string {
  return "word ".repeat(Math.ceil(len / 5)).slice(0, len);
}

function noisyText(): string {
  const signal = " cookie subscribe javascript log in sign up cookie ";
  return signal.repeat(3).padEnd(600, "x");
}

function frontmatterText(): string {
  return [
    "---",
    "relevance_score: 0.9",
    "intent_category: informational",
    "token_estimate: 200",
    "last_updated: 2026-01-01",
    "---",
    longText(),
  ].join("\n");
}

function anchorText(): string {
  return [
    "[ANCHOR: SUMMARY]",
    "[ANCHOR: TECHNICAL_DETAILS]",
    "[ANCHOR: COMPARISON]",
    "[ANCHOR: CITATIONS]",
    longText(),
  ].join("\n");
}

describe("scoreContent", () => {
  it("empty string returns tooShort=true, acceptable=false", () => {
    const result = scoreContent("");
    expect(result.tooShort).toBe(true);
    expect(result.acceptable).toBe(false);
  });

  it("short text (< 500 chars) returns tooShort=true", () => {
    const result = scoreContent("short");
    expect(result.tooShort).toBe(true);
  });

  it("long text with links returns tooShort=false, missingLinks=false", () => {
    const result = scoreContent(longText(), ["https://example.com"]);
    expect(result.tooShort).toBe(false);
    expect(result.missingLinks).toBe(false);
  });

  it("text without links returns missingLinks=true", () => {
    const result = scoreContent(longText());
    expect(result.missingLinks).toBe(true);
  });

  it("duplicate-heavy text detected", () => {
    const lines = Array(30).fill("repeated line").join("\n");
    const result = scoreContent(lines);
    expect(result.duplicateHeavy).toBe(true);
  });

  it("noisy requires more than 6 signals but only 5 exist, so never triggers", () => {
    const result = scoreContent(noisyText(), ["https://example.com"]);
    expect(result.noisy).toBe(false);
  });

  it("frontmatter bonus applied", () => {
    const withFm = scoreContent(frontmatterText(), ["https://example.com"]);
    const withoutFm = scoreContent(longText(), ["https://example.com"]);
    expect(withFm.score).toBeGreaterThan(withoutFm.score);
  });

  it("anchors bonus applied", () => {
    const withAnchors = scoreContent(anchorText(), ["https://example.com"]);
    const withoutAnchors = scoreContent(longText(), ["https://example.com"]);
    expect(withAnchors.score).toBeGreaterThan(withoutAnchors.score);
  });

  it("score clamped to [0, 1]", () => {
    const low = scoreContent("");
    expect(low.score).toBeGreaterThanOrEqual(0);

    const high = scoreContent(frontmatterText(), ["https://example.com"]);
    expect(high.score).toBeLessThanOrEqual(1);
  });

  it("acceptable requires score >= 0.65 and not tooShort", () => {
    const tooShort = scoreContent("hi");
    expect(tooShort.acceptable).toBe(false);

    const good = scoreContent(longText(), ["https://example.com"]);
    expect(good.acceptable).toBe(true);
  });

  it("null/undefined markdown handled gracefully", () => {
    const resultNull = scoreContent(null as unknown as string);
    expect(resultNull.tooShort).toBe(true);
    expect(resultNull.acceptable).toBe(false);

    const resultUndef = scoreContent(undefined as unknown as string);
    expect(resultUndef.tooShort).toBe(true);
    expect(resultUndef.acceptable).toBe(false);
  });
});

describe("extractLinks", () => {
  it("extracts markdown inline links", () => {
    const links = extractLinks(
      "See [the docs](https://example.com/docs) and [more](https://example.org)."
    );

    expect(links).toHaveLength(2);
    expect(links.some((l) => l.includes("example.com/docs"))).toBe(true);
  });

  it("extracts angle-bracket autolinks", () => {
    expect(extractLinks("Visit <https://example.com/page> today")).not.toHaveLength(0);
  });

  it("returns empty for non-markdown and empty input", () => {
    expect(extractLinks("plain text with no links at all")).toEqual([]);
    expect(extractLinks("")).toEqual([]);
  });
});

describe("link inference parity with scripts/quality.py", () => {
  const body = "Useful documentation prose. ".repeat(40);

  it("infers links when no list is supplied, so markdown links are not penalised", () => {
    const inferred = scoreContent(body + "\n[ref](https://example.com/a)");

    expect(inferred.missingLinks).toBe(false);

    const baseline = scoreContent(body);
    expect(baseline.missingLinks).toBe(true);
    expect(baseline.score).toBeLessThan(inferred.score);
  });

  it("treats an explicitly empty list as no links", () => {
    expect(scoreContent(body, []).missingLinks).toBe(true);
  });

  it("an explicit list wins over inference", () => {
    expect(scoreContent(body, ["https://example.com"]).missingLinks).toBe(false);
    expect(scoreContent(body, []).missingLinks).toBe(true);
  });
});

function relevantBody(): string {
  return Array.from(
    { length: 12 },
    (_, i) => `Use the Python asyncio event loop to run coroutines and tasks. Section ${i}.`
  ).join("\n");
}

function irrelevantBody(): string {
  return Array.from(
    { length: 12 },
    (_, i) => `Kubernetes schedules pods across cluster nodes and services. Section ${i}.`
  ).join("\n");
}

describe("scoreContent query relevance", () => {
  it("scores on-topic content above off-topic content", () => {
    const relevant = scoreContent(relevantBody(), undefined, "python asyncio");
    const irrelevant = scoreContent(irrelevantBody(), undefined, "python asyncio");

    expect(relevant.relevance).toBe(1);
    expect(irrelevant.relevance).toBe(0);
    expect(irrelevant.score).toBeLessThan(relevant.score);
    expect(irrelevant.acceptable).toBe(false);
  });

  it("applies the same proportional discount as Python", () => {
    const relevant = scoreContent(relevantBody(), undefined, "python asyncio");
    const irrelevant = scoreContent(irrelevantBody(), undefined, "python asyncio");

    // Mirrors RELEVANCE_WEIGHT = 0.35 in scripts/quality.py.
    expect(irrelevant.score).toBeCloseTo(relevant.score * (1 - 0.35), 5);
  });

  it("without a query the heuristic score is unchanged", () => {
    const baseline = scoreContent(relevantBody());

    expect(scoreContent(relevantBody(), undefined, undefined).score).toBe(baseline.score);
    expect(baseline.relevance).toBe(1);
  });

  it("queries without usable terms disable the blend", () => {
    const scored = scoreContent(irrelevantBody(), undefined, "to be or");

    expect(scored.relevance).toBe(1);
    expect(scored.score).toBe(scoreContent(irrelevantBody()).score);
  });

  it("partial overlap sits between the extremes", () => {
    const relevant = scoreContent(relevantBody(), undefined, "python asyncio");
    const partial = scoreContent(relevantBody(), undefined, "python kubernetes");
    const irrelevant = scoreContent(irrelevantBody(), undefined, "python asyncio");

    expect(partial.relevance).toBeCloseTo(0.5, 5);
    expect(irrelevant.score).toBeLessThan(partial.score);
    expect(partial.score).toBeLessThan(relevant.score);
  });
});
