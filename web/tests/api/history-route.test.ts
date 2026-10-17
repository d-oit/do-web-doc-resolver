import { describe, expect, it } from "vitest";
import { NextRequest } from "next/server";

import { DELETE, GET, POST } from "../../app/api/history/route";
import { MAX_BODY_BYTES } from "../../lib/body-limit";

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
    const postReq = new NextRequest("http://localhost/api/history", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        cookie: "ui-session=test-history-session",
      },
      body: JSON.stringify({
        query: "rust async tutorial",
        result: "# Rust Async",
        provider: "jina",
      }),
    });

    const postRes = await POST(postReq);
    expect(postRes.status).toBe(200);
    const postData = await postRes.json();
    expect(postData.ok).toBe(true);
    expect(postData.id).toBeDefined();

    const getReq = new NextRequest("http://localhost/api/history", {
      headers: { cookie: "ui-session=test-history-session" },
    });

    const getRes = await GET(getReq);
    expect(getRes.status).toBe(200);
    const getData = await getRes.json();
    expect(getData.entries.length).toBeGreaterThanOrEqual(1);
    expect(getData.entries[0].query).toBe("rust async tutorial");
  });

  it("deletes a history entry by id", async () => {
    const postReq = new NextRequest("http://localhost/api/history", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        cookie: "ui-session=test-delete-session",
      },
      body: JSON.stringify({ query: "to be deleted" }),
    });

    const postRes = await POST(postReq);
    const { id } = await postRes.json();

    const deleteReq = new NextRequest(`http://localhost/api/history?id=${id}`, {
      method: "DELETE",
      headers: { cookie: "ui-session=test-delete-session" },
    });

    const deleteRes = await DELETE(deleteReq);
    expect(deleteRes.status).toBe(200);

    const getReq = new NextRequest("http://localhost/api/history", {
      headers: { cookie: "ui-session=test-delete-session" },
    });
    const getData = await (await GET(getReq)).json();
    expect(getData.entries.find((e: { id: string }) => e.id === id)).toBeUndefined();
  });
});
