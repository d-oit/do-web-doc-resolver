import { describe, expect, it } from "vitest";
import { NextRequest } from "next/server";

import { DELETE, GET, POST } from "../../app/api/history/route";
import { MAX_BODY_BYTES } from "../../lib/body-limit";
import { createSessionToken, SESSION_COOKIE, verifySessionToken } from "../../lib/session";

function cookieHeader(token: string): string {
  return `${SESSION_COOKIE}=${token}`;
}

function requestWithCookie(
  url: string,
  token: string,
  method: "GET" | "POST" | "DELETE",
  body?: string
): NextRequest {
  return new NextRequest(url, {
    method,
    headers: {
      "content-type": "application/json",
      cookie: cookieHeader(token),
    },
    ...(body !== undefined ? { body } : {}),
  });
}

async function postEntry(token: string, body: object): Promise<string> {
  const res = await POST(requestWithCookie("http://localhost/api/history", token, "POST", JSON.stringify(body)));
  expect(res.status).toBe(200);
  const data = await res.json();
  expect(data.ok).toBe(true);
  return data.id as string;
}

function entriesOf(data: { entries?: unknown[] }): { id: string; query: string }[] {
  return (data.entries || []) as { id: string; query: string }[];
}

describe("/api/history route", () => {
  it("rejects an oversized body with 413 Payload Too Large", async () => {
    const postReq = new NextRequest("http://localhost/api/history", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ query: "test", padding: "x".repeat(MAX_BODY_BYTES + 64) }),
    });

    const postRes = await POST(postReq);
    expect(postRes.status).toBe(413);
    const data = await postRes.json();
    expect(data.error).toContain("Request body exceeds");
  });

  it("saves and retrieves history entries", async () => {
    const { token } = createSessionToken();

    const id = await postEntry(token, {
      query: "rust async tutorial",
      result: "# Rust Async",
      provider: "jina",
    });
    expect(id).toBeDefined();

    const getRes = await GET(requestWithCookie("http://localhost/api/history", token, "GET"));
    expect(getRes.status).toBe(200);
    const entries = entriesOf(await getRes.json());
    expect(entries.length).toBeGreaterThanOrEqual(1);
    expect(entries[0]?.query).toBe("rust async tutorial");
    expect(entries[0]?.id).toBe(id);
  });

  it("issues a signed cookie to a first-time visitor", async () => {
    const getRes = await GET(new NextRequest("http://localhost/api/history"));

    expect(getRes.status).toBe(200);
    expect(entriesOf(await getRes.json())).toEqual([]);

    const setCookie = getRes.cookies.get(SESSION_COOKIE);
    expect(setCookie).toBeDefined();
    expect(setCookie?.httpOnly).toBe(true);
    expect(verifySessionToken(setCookie?.value)).not.toBeNull();
  });

  it("gives a forged cookie a fresh empty session, not the original partition", async () => {
    const { token, sessionId: legitId } = createSessionToken();
    await postEntry(token, { query: "legit session entry", result: "", provider: "jina" });

    const res = await GET(
      new NextRequest("http://localhost/api/history", {
        headers: { cookie: cookieHeader(`${legitId}.tampered`) },
      })
    );

    expect(res.status).toBe(200);
    expect(entriesOf(await res.json())).toEqual([]);
    expect(res.cookies.get(SESSION_COOKIE)).toBeDefined();
  });

  it("keeps two independent sessions isolated", async () => {
    const { token: tokenA } = createSessionToken();
    const { token: tokenB } = createSessionToken();

    const aId = await postEntry(tokenA, { query: "session a entry", result: "", provider: "jina" });
    const bId = await postEntry(tokenB, { query: "session b entry", result: "", provider: "jina" });

    const dataA = entriesOf(await (await GET(requestWithCookie("http://localhost/api/history", tokenA, "GET"))).json());
    const dataB = entriesOf(await (await GET(requestWithCookie("http://localhost/api/history", tokenB, "GET"))).json());

    expect(dataA.map((e) => e.id)).toContain(aId);
    expect(dataA.map((e) => e.id)).not.toContain(bId);
    expect(dataB.map((e) => e.id)).toContain(bId);
    expect(dataB.map((e) => e.id)).not.toContain(aId);
  });

  it("searches only within the caller's session", async () => {
    const { token: tokenA } = createSessionToken();
    const { token: tokenB } = createSessionToken();

    await postEntry(tokenA, { query: "needle in session a", result: "", provider: "jina" });

    const dataB = entriesOf(
      await (await GET(requestWithCookie("http://localhost/api/history?q=needle", tokenB, "GET"))).json()
    );
    expect(dataB).toEqual([]);
  });

  it("deletes a history entry by id", async () => {
    const { token } = createSessionToken();
    const id = await postEntry(token, { query: "to be deleted", result: "", provider: "jina" });

    const deleteRes = await DELETE(requestWithCookie(`http://localhost/api/history?id=${id}`, token, "DELETE"));
    expect(deleteRes.status).toBe(200);

    const getData = await (await GET(requestWithCookie("http://localhost/api/history", token, "GET"))).json();
    expect(entriesOf(getData).find((e) => e.id === id)).toBeUndefined();
  });

  it("cannot delete another session's entry", async () => {
    const { token: ownerToken } = createSessionToken();
    const { token: attackerToken } = createSessionToken();

    const id = await postEntry(ownerToken, { query: "belongs to someone else", result: "", provider: "jina" });

    const deleteRes = await DELETE(requestWithCookie(`http://localhost/api/history?id=${id}`, attackerToken, "DELETE"));
    expect(deleteRes.status).toBe(200);

    const ownerData = entriesOf(await (await GET(requestWithCookie("http://localhost/api/history", ownerToken, "GET"))).json());
    expect(ownerData.find((e) => e.id === id)).toBeDefined();
  });
});
