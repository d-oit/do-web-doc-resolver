import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import {
  checkRateLimit,
  clearRateLimits,
  getRateLimitStats,
  cleanupExpiredEntries,
  getClientIdentifier,
  enforceRateLimit,
  getRateLimitStore,
  setRateLimitStoreForTesting,
  MemoryRateLimitStore,
  UpstashRestRateLimitStore,
  MAX_TRACKED_CLIENTS,
  type RateLimitStore,
} from "../lib/rate-limit";

describe("rate limiting", () => {
  beforeEach(() => {
    clearRateLimits();
  });

  describe("checkRateLimit", () => {
    it("allows first request", () => {
      const result = checkRateLimit("test-client");
      expect(result.allowed).toBe(true);
      expect(result.remaining).toBe(29);
    });

    it("increments count on subsequent requests", () => {
      checkRateLimit("test-client");
      checkRateLimit("test-client");
      const result = checkRateLimit("test-client");
      expect(result.allowed).toBe(true);
      expect(result.remaining).toBe(27);
    });

    it("blocks when limit exceeded", () => {
      const config = { windowMs: 60000, maxRequests: 3 };
      checkRateLimit("test-client", config);
      checkRateLimit("test-client", config);
      checkRateLimit("test-client", config);
      const result = checkRateLimit("test-client", config);
      expect(result.allowed).toBe(false);
      expect(result.remaining).toBe(0);
    });

    it("resets after window expires", () => {
      const config = { windowMs: 10, maxRequests: 1 }; // 10ms window
      checkRateLimit("test-client", config);

      // Wait for window to expire
      return new Promise<void>((resolve) => {
        setTimeout(() => {
          const result = checkRateLimit("test-client", config);
          expect(result.allowed).toBe(true);
          resolve();
        }, 20);
      });
    });

    it("tracks different clients separately", () => {
      const result1 = checkRateLimit("client-1");
      const result2 = checkRateLimit("client-2");
      expect(result1.allowed).toBe(true);
      expect(result2.allowed).toBe(true);
    });
  });

  describe("getRateLimitStats", () => {
    it("returns correct stats", () => {
      checkRateLimit("client-1");
      checkRateLimit("client-2");
      const stats = getRateLimitStats();
      expect(stats.totalEntries).toBe(2);
      expect(stats.activeEntries).toBe(2);
    });
  });

  describe("cleanupExpiredEntries", () => {
    it("removes expired entries", async () => {
      const config = { windowMs: 10, maxRequests: 1 };
      checkRateLimit("old-client", config);

      // Wait for expiry
      await new Promise<void>((resolve) => setTimeout(resolve, 20));

      const cleaned = cleanupExpiredEntries();
      expect(cleaned).toBe(1);

      const stats = getRateLimitStats();
      expect(stats.totalEntries).toBe(0);
    });
  });

  describe("getClientIdentifier", () => {
    afterEach(() => {
      vi.unstubAllEnvs();
    });

    it("prioritizes x-real-ip over x-forwarded-for when the proxy is trusted", () => {
      vi.stubEnv("RATE_LIMIT_TRUST_PROXY", "1");
      const headers = new Headers({
        "x-forwarded-for": "1.2.3.4, 5.6.7.8",
        "x-real-ip": "9.9.9.9",
      });
      const request = { headers } as unknown as Request;
      expect(getClientIdentifier(request)).toBe(getClientIdentifier({ headers: new Headers({ "x-real-ip": "9.9.9.9" }) } as unknown as Request));
    });

    it("falls back to the first x-forwarded-for value when the proxy is trusted", () => {
      vi.stubEnv("RATE_LIMIT_TRUST_PROXY", "1");
      const headers = new Headers({
        "x-forwarded-for": "1.2.3.4, 5.6.7.8",
      });
      const request = { headers } as unknown as Request;
      expect(getClientIdentifier(request)).toBe(getClientIdentifier({ headers: new Headers({ "x-real-ip": "1.2.3.4" }) } as unknown as Request));
    });

    it("returns a shared identifier when no platform IP headers are trusted", () => {
      const headers = new Headers();
      const request = { headers } as unknown as Request;
      const identifier = getClientIdentifier(request);
      expect(identifier).toHaveLength(32);
      expect(getClientIdentifier({ headers: new Headers() } as unknown as Request)).toBe(identifier);
    });
  });
});

describe("distributed enforcement", () => {
  beforeEach(() => {
    clearRateLimits();
    setRateLimitStoreForTesting(undefined);
    vi.unstubAllEnvs();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    setRateLimitStoreForTesting(undefined);
  });

  it("shares one counter across instances via the distributed store", async () => {
    const store = new MemoryRateLimitStore();
    setRateLimitStoreForTesting(store);
    const config = { windowMs: 60000, maxRequests: 2 };

    const first = await store.hit("resolve:client-a", config);
    const second = await store.hit("resolve:client-a", config);
    const third = await store.hit("resolve:client-a", config);

    expect(first.allowed).toBe(true);
    expect(second.allowed).toBe(true);
    expect(third.allowed).toBe(false);
    expect(third.remaining).toBe(0);
  });

  it("upstash store issues an atomic eval and parses the result", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ result: "[2,59000]" }), { status: 200 })
    );
    vi.stubGlobal("fetch", fetchMock);

    const store = new UpstashRestRateLimitStore("https://cache.example.com", "token");
    const result = await store.hit("resolve:client-a", { windowMs: 60000, maxRequests: 1 });

    expect(result.allowed).toBe(false);
    expect(result.remaining).toBe(0);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("https://cache.example.com/eval");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer token");
    const body = JSON.parse(init.body as string) as string[];
    expect(body[1]).toBe("ratelimit:resolve:client-a");
    expect(body[2]).toBe("60000");
  });

  it("fail-closed blocks requests when the store fails", async () => {
    vi.stubEnv("RATE_LIMIT_FAILURE_MODE", "fail-closed");
    const failing: RateLimitStore = {
      hit: async () => {
        throw new Error("backend down");
      },
    };
    setRateLimitStoreForTesting(failing);

    const result = await enforceRateLimit("client-a", "resolve");

    expect(result.allowed).toBe(false);
    expect(result.remaining).toBe(0);
  });

  it("fail-open allows requests when the store fails", async () => {
    vi.stubEnv("RATE_LIMIT_FAILURE_MODE", "fail-open");
    const failing: RateLimitStore = {
      hit: async () => {
        throw new Error("backend down");
      },
    };
    setRateLimitStoreForTesting(failing);

    const result = await enforceRateLimit("client-a", "resolve");

    expect(result.allowed).toBe(true);
  });

  it("bounds memory-store cardinality by evicting entries", async () => {
    for (let i = 0; i < MAX_TRACKED_CLIENTS + 5; i++) {
      checkRateLimit(`client-${i}`, { windowMs: 60000, maxRequests: 1 });
    }
    expect(getRateLimitStats().totalEntries).toBeLessThanOrEqual(MAX_TRACKED_CLIENTS);
  });

  it("expired keys are reclaimed automatically", async () => {
    checkRateLimit("ephemeral-client", { windowMs: 5, maxRequests: 1 });
    await new Promise((resolve) => setTimeout(resolve, 15));
    expect(cleanupExpiredEntries()).toBeGreaterThan(0);
    expect(getRateLimitStats().activeEntries).toBe(0);
  });
});

describe("trusted client identity", () => {
  beforeEach(() => {
    clearRateLimits();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  function fakeRequest(headers: Record<string, string>): Request {
    return new Request("http://localhost/api/resolve", { headers });
  }

  it("ignores user-supplied forwarding headers when the proxy is untrusted", () => {
    vi.stubEnv("RATE_LIMIT_TRUST_PROXY", "0");
    delete process.env.VERCEL;

    const identifier = getClientIdentifier(
      fakeRequest({ "x-forwarded-for": "1.2.3.4", "x-real-ip": "5.6.7.8" })
    );

    expect(identifier).not.toContain("1.2.3.4");
    expect(identifier).not.toContain("5.6.7.8");
  });

  it("trusts platform-set headers when the proxy is trusted", () => {
    vi.stubEnv("RATE_LIMIT_TRUST_PROXY", "1");

    const identifier = getClientIdentifier(
      fakeRequest({ "x-real-ip": "203.0.113.9", "x-forwarded-for": "1.2.3.4" })
    );

    expect(identifier).toHaveLength(32);
    expect(identifier).toBe(getClientIdentifier(fakeRequest({ "x-real-ip": "203.0.113.9" })));
  });

  it("ignores spoofed x-forwarded-for when x-real-ip is set by the platform", () => {
    vi.stubEnv("RATE_LIMIT_TRUST_PROXY", "1");

    const real = getClientIdentifier(fakeRequest({ "x-real-ip": "203.0.113.9" }));
    const spoofed = getClientIdentifier(
      fakeRequest({ "x-real-ip": "203.0.113.9", "x-forwarded-for": "6.6.6.6" })
    );

    expect(spoofed).toBe(real);
  });
});

