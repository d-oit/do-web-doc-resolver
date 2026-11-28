import { beforeEach, describe, expect, it, vi } from "vitest";

const { mockValidateUrlForFetchAsync, mockSsrfFetch } = vi.hoisted(() => ({
  mockValidateUrlForFetchAsync: vi.fn(),
  mockSsrfFetch: vi.fn(),
}));

vi.mock("@/lib/validation", () => ({
  validateUrlForFetchAsync: mockValidateUrlForFetchAsync,
}));

vi.mock("@/lib/ssrf-fetch", () => ({
  ssrfFetch: mockSsrfFetch,
}));

import { extractViaJina, extractViaFirecrawl, extractViaMistralBrowser } from "../lib/resolvers/url";
import { Logger } from "../lib/log";

describe("extractViaJina", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("blocks private target URLs before calling the Jina proxy", async () => {
    mockValidateUrlForFetchAsync.mockResolvedValueOnce({
      valid: false,
      error: "Private/internal URLs are not allowed",
    });

    const result = await extractViaJina("http://127.0.0.1/private", new Logger("error"));

    expect(result).toBeNull();
    expect(mockValidateUrlForFetchAsync).toHaveBeenCalledWith("http://127.0.0.1/private");
    expect(mockSsrfFetch).not.toHaveBeenCalled();
  });

  it("fetches through Jina after validating the target URL", async () => {
    mockValidateUrlForFetchAsync.mockResolvedValue({ valid: true });
    mockSsrfFetch.mockResolvedValue(
      new Response("x".repeat(250), {
        status: 200,
        headers: { "Content-Type": "text/plain" },
      })
    );

    const result = await extractViaJina("https://example.com/docs", new Logger("error"));

    expect(result).toBe("x".repeat(250));
    expect(mockValidateUrlForFetchAsync).toHaveBeenCalledWith("https://example.com/docs");
    expect(mockSsrfFetch).toHaveBeenCalledWith(
      "https://r.jina.ai/https://example.com/docs",
      expect.objectContaining({ headers: expect.objectContaining({ Accept: "text/plain" }) })
    );
  });
});

describe("extractViaFirecrawl", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("blocks private target URLs before calling Firecrawl API", async () => {
    mockValidateUrlForFetchAsync.mockResolvedValueOnce({
      valid: false,
      error: "Private/internal URLs are not allowed",
    });

    const result = await extractViaFirecrawl("http://127.0.0.1/private", "test-key", new Logger("error"));

    expect(result).toBeNull();
    expect(mockValidateUrlForFetchAsync).toHaveBeenCalledWith("http://127.0.0.1/private");
    expect(mockSsrfFetch).not.toHaveBeenCalled();
  });
});

describe("extractViaMistralBrowser", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("blocks private target URLs before calling Mistral API", async () => {
    mockValidateUrlForFetchAsync.mockResolvedValueOnce({
      valid: false,
      error: "Private/internal URLs are not allowed",
    });

    const result = await extractViaMistralBrowser("http://127.0.0.1/private", "test-key", new Logger("error"));

    expect(result).toBeNull();
    expect(mockValidateUrlForFetchAsync).toHaveBeenCalledWith("http://127.0.0.1/private");
    expect(mockSsrfFetch).not.toHaveBeenCalled();
  });
});
