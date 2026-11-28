import { describe, expect, it } from "vitest";
import nextConfig from "../next.config.mjs";

describe("next.config image allowlist", () => {
  const patterns = nextConfig.images?.remotePatterns ?? [];

  it("contains no wildcard hostnames", () => {
    for (const pattern of patterns) {
      expect(pattern.hostname).not.toBe("**");
      expect(pattern.hostname).not.toContain("*");
    }
  });

  it("allows only HTTPS remote hosts", () => {
    for (const pattern of patterns) {
      expect(pattern.protocol).toBe("https");
    }
  });

  it("allows only non-loopback hosts so the optimizer cannot reach private addresses", () => {
    const forbidden = [
      "localhost",
      "127.0.0.1",
      "0.0.0.0",
      "169.254.169.254",
      "metadata.google.internal",
      "[::1]",
    ];
    for (const pattern of patterns) {
      expect(forbidden).not.toContain(pattern.hostname.toLowerCase());
    }
  });
});
