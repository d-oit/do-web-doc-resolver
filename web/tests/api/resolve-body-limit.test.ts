import { describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("../../lib/routing", () => ({
  ResolutionBudget: vi.fn().mockImplementation(() => ({
    canTry: vi.fn().mockReturnValue(true),
    recordAttempt: vi.fn(),
    getState: vi.fn().mockReturnValue({}),
  })),
  planProviderOrder: vi.fn().mockReturnValue(["jina"]),
  detectJsHeavy: vi.fn().mockReturnValue(false),
  isPaidProvider: vi.fn().mockReturnValue(false),
}));

vi.mock("../../lib/validation", () => ({
  validateResolveRequest: vi.fn().mockImplementation((body) => ({
    success: true,
    data: body,
  })),
  validateUrlForFetchAsync: vi.fn().mockResolvedValue({ valid: true }),
}));

vi.mock("../../lib/cache", () => ({
  get: vi.fn().mockResolvedValue(null),
  set: vi.fn().mockResolvedValue(true),
}));

vi.mock("../../lib/records", () => ({
  save: vi.fn(),
}));

import { POST } from "../../app/api/resolve/route";
import { MAX_BODY_BYTES } from "../../lib/body-limit";

describe("POST /api/resolve body limit", () => {
  it("rejects an oversized body with 413 Payload Too Large", async () => {
    const postReq = new NextRequest("http://localhost/api/resolve", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ query: "test", padding: "x".repeat(MAX_BODY_BYTES + 64) }),
    });

    const postRes = await POST(postReq);
    expect(postRes.status).toBe(413);
    const data = await postRes.json();
    expect(data.error).toContain("Request body exceeds");
  });
});
