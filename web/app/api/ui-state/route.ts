import { NextRequest, NextResponse } from "next/server";
import crypto from "crypto";

// In-memory store for UI state (sessionId -> UIState with TTL)
interface StoredState {
  data: Record<string, unknown>;
  expiresAt: number;
}

const stateStore = new Map<string, StoredState>();
const ONE_YEAR_MS = 365 * 24 * 60 * 60 * 1000;

// Simple in-memory store with TTL cleanup
function cleanupExpiredStates(): void {
  const now = Date.now();
  for (const [sessionId, stored] of stateStore.entries()) {
    if (stored.expiresAt < now) {
      stateStore.delete(sessionId);
    }
  }
}

// Generate anonymous session ID from IP + User-Agent (SHA256)
function getSessionId(request: NextRequest): string {
  const ip = request.headers.get("x-forwarded-for") || 
             request.headers.get("x-real-ip") || 
             "127.0.0.1";
  const userAgent = request.headers.get("user-agent") || "";
  
  const hash = crypto.createHash("sha256");
  hash.update(`${ip}:${userAgent}`);
  return hash.digest("hex");
}

// GET endpoint: Get UI state for session
export async function GET(request: NextRequest) {
  try {
    cleanupExpiredStates();
    
    const sessionId = getSessionId(request);
    const stored = stateStore.get(sessionId);
    
    if (!stored || stored.expiresAt < Date.now()) {
      return NextResponse.json({});
    }
    
    return NextResponse.json(stored.data);
  } catch {
    return NextResponse.json({ error: "Failed to load state" }, { status: 500 });
  }
}

// POST endpoint: Save UI state
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    if (!body || typeof body !== "object" || Array.isArray(body)) {
      return NextResponse.json({ error: "Invalid state payload" }, { status: 400 });
    }
    
    const sessionId = getSessionId(request);
    const now = Date.now();
    
    // Store with 1-year TTL
    stateStore.set(sessionId, {
      data: body as Record<string, unknown>,
      expiresAt: now + ONE_YEAR_MS,
    });
    
    return NextResponse.json({ ok: true, lastUpdated: now });
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }
}
