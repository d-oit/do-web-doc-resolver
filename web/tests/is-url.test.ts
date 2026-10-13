import { describe, it, expect } from "vitest";
import { isUrl } from "../lib/is-url";

// The page's mode label and the API route's execution path both use this
// predicate; a divergence makes the UI promise one mode and run another.
describe("isUrl", () => {
  it("accepts http and https URLs", () => {
    expect(isUrl("http://example.com")).toBe(true);
    expect(isUrl("https://example.com/path?query=1")).toBe(true);
    expect(isUrl("HTTPS://EXAMPLE.COM")).toBe(true);
  });

  it("trims surrounding whitespace", () => {
    expect(isUrl("  https://example.com  ")).toBe(true);
    expect(isUrl("\nhttps://example.com\n")).toBe(true);
  });

  it("rejects non-URLs and non-http schemes", () => {
    expect(isUrl("example.com")).toBe(false);
    expect(isUrl("python async best practices")).toBe(false);
    expect(isUrl("ftp://example.com")).toBe(false);
    expect(isUrl("")).toBe(false);
    expect(isUrl("   ")).toBe(false);
  });

  it("rejects strings with whitespace inside the URL", () => {
    expect(isUrl("https://example.com/a b")).toBe(false);
  });
});
