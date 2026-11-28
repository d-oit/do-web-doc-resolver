import { describe, expect, it, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";
import { POST } from "../../app/api/resolve/route";
import { proxy } from "../../proxy";

// Rate limiting runs in two layers: web/proxy.ts (the App Router file
// convention that replaced middleware.ts in Next 16) is a cheap edge
// pre-gate on the "resolve" scope; the route handler enforces the
// authoritative "resolve_route" budget plus the shared "global_provider"
// ceiling on its own counters, so neither layer is the sole security
// boundary.
vi.mock("../../lib/rate-limit", () => ({
  checkRateLimit: vi.fn(),
  getClientIdentifier: vi.fn(),
  enforceRateLimit: vi.fn(),
}));

vi.mock("../../lib/cache", () => ({
  get: vi.fn().mockResolvedValue(null),
  set: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("../../lib/records", () => ({
  save: vi.fn(),
}));

vi.mock("../../lib/resolvers/index", () => ({
  isUrl: vi.fn().mockReturnValue(false),
  queryProviders: {},
  urlProviders: {},
}));

import * as rateLimit from "../../lib/rate-limit";

function resolveRequest(): NextRequest {
  return new NextRequest("http://localhost/api/resolve", {
    method: "POST",
    body: JSON.stringify({ query: "test" }),
  });
}

describe("POST /api/resolve rate limiting", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(rateLimit.getClientIdentifier).mockReturnValue("test-ip");
    vi.mocked(rateLimit.enforceRateLimit).mockResolvedValue({
      allowed: true,
      remaining: 29,
      resetAt: Date.now() + 60000,
    });
  });

  it("proxy returns 429 when rate limit is exceeded", async () => {
    vi.mocked(rateLimit.enforceRateLimit).mockResolvedValue({
      allowed: false,
      remaining: 0,
      resetAt: Date.now() + 60000,
    });

    const request = resolveRequest();
    const response = await proxy(request);

    expect(response.status).toBe(429);
    expect(rateLimit.getClientIdentifier).toHaveBeenCalledWith(request);
    expect(rateLimit.enforceRateLimit).toHaveBeenCalledWith("test-ip", "resolve");
  });

  it("proxy allows the request and exposes rate limit headers", async () => {
    const response = await proxy(resolveRequest());

    expect(response.status).toBe(200);
    expect(response.headers.get("X-RateLimit-Remaining")).toBe("29");
  });

  it("route handler enforces its own budget and the global provider ceiling", async () => {
    const response = await POST(resolveRequest());

    expect(response.status).not.toBe(429);
    expect(rateLimit.enforceRateLimit).toHaveBeenCalledWith("test-ip", "resolve_route");
    expect(rateLimit.enforceRateLimit).toHaveBeenCalledWith("test-ip", "global_provider");
  });

  it("route handler returns 429 when the route budget is exhausted", async () => {
    vi.mocked(rateLimit.enforceRateLimit).mockImplementation(async (identifier, scope) => {
      if (scope === "resolve_route") {
        return { allowed: false, remaining: 0, resetAt: Date.now() + 60000 };
      }
      return { allowed: true, remaining: 10, resetAt: Date.now() + 60000 };
    });

    const response = await POST(resolveRequest());

    expect(response.status).toBe(429);
    expect(response.headers.get("Retry-After")).toBeTruthy();
  });

  it("route handler enforces the stricter deep-research budget", async () => {
    const request = new NextRequest("http://localhost/api/resolve", {
      method: "POST",
      body: JSON.stringify({ query: "test", deepResearch: true }),
    });

    await POST(request);

    expect(rateLimit.enforceRateLimit).toHaveBeenCalledWith("test-ip", "resolve_deep");
  });

  it("route handler returns 503 when the rate limit backend fails closed", async () => {
    vi.mocked(rateLimit.enforceRateLimit).mockRejectedValue(new Error("store down"));

    const response = await POST(resolveRequest());

    expect(response.status).toBe(503);
  });
});
