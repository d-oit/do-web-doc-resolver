import { describe, expect, it, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";
import { POST } from "../../app/api/resolve/route";
import { proxy } from "../../proxy";

// Rate limiting is enforced in web/proxy.ts (the App Router file convention
// that replaced middleware.ts in Next 16). The route handler used to call
// checkRateLimit as well, which consumed the same in-memory counter twice
// and halved the effective limit to 15 req/min.
vi.mock("../../lib/rate-limit", () => ({
  checkRateLimit: vi.fn(),
  getClientIdentifier: vi.fn(),
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
  });

  it("proxy returns 429 when rate limit is exceeded", () => {
    vi.mocked(rateLimit.getClientIdentifier).mockReturnValue("test-ip");
    vi.mocked(rateLimit.checkRateLimit).mockReturnValue({
      allowed: false,
      remaining: 0,
      resetAt: Date.now() + 60000,
    });

    const request = resolveRequest();
    const response = proxy(request);

    expect(response.status).toBe(429);
    expect(rateLimit.getClientIdentifier).toHaveBeenCalledWith(request);
    expect(rateLimit.checkRateLimit).toHaveBeenCalledWith("test-ip", expect.any(Object));
  });

  it("proxy allows the request and exposes rate limit headers", () => {
    vi.mocked(rateLimit.getClientIdentifier).mockReturnValue("test-ip");
    vi.mocked(rateLimit.checkRateLimit).mockReturnValue({
      allowed: true,
      remaining: 29,
      resetAt: Date.now() + 60000,
    });

    const response = proxy(resolveRequest());

    expect(response.status).toBe(200);
    expect(response.headers.get("X-RateLimit-Remaining")).toBe("29");
  });

  it("route handler does not consume the rate limit counter itself", async () => {
    // Proceeding past the gate means the cascade runs; "No search results found"
    // is an acceptable outcome as long as it is not a 429.
    const response = await POST(resolveRequest());

    expect(response.status).not.toBe(429);
    expect(rateLimit.checkRateLimit).not.toHaveBeenCalled();
  });
});
