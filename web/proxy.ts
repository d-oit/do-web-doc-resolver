import { NextRequest, NextResponse } from "next/server";
import { enforceRateLimit, getClientIdentifier } from "@/lib/rate-limit";

function nowMs(): number {
  return globalThis.performance.timeOrigin + performance.now();
}

export async function proxy(request: NextRequest) {
  if (request.method !== "POST") {
    return NextResponse.next();
  }

  // Exact path, not a prefix test: `startsWith` would also capture a sibling
  // route such as `/api/resolve-stats` and rate-limit it by accident.
  if (request.nextUrl.pathname !== "/api/resolve") {
    return NextResponse.next();
  }

  // Cheap pre-gate at the edge; the authoritative budget is enforced in the
  // route handler with its own counter, so neither is a single point of
  // failure for cost protection.
  const identifier = getClientIdentifier(request);
  const { allowed, remaining, resetAt } = await enforceRateLimit(identifier, "resolve");

  if (!allowed) {
    const retryAfter = Math.max(1, Math.ceil((resetAt - nowMs()) / 1000));
    return NextResponse.json(
      { error: "Rate limit exceeded. Try again later." },
      { status: 429, headers: { "Retry-After": String(retryAfter) } }
    );
  }

  const response = NextResponse.next();
  response.headers.set("X-RateLimit-Remaining", String(remaining));
  response.headers.set("X-RateLimit-Reset", String(Math.ceil(resetAt / 1000)));
  return response;
}

export const config = {
  // Narrower than `/api/:path*`: only the route that actually calls a paid
  // provider belongs here. Widening the matcher would gate cheap endpoints and
  // spend in-memory counter entries on every API call.
  matcher: ["/api/resolve"],
};
