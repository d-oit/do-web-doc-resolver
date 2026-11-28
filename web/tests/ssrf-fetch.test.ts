import { describe, expect, it } from "vitest";
import http from "node:http";
import type { AddressInfo } from "node:net";
import {
  SsrfBlockedError,
  resolvePinnedAddress,
  ssrfFetch,
  type LookupFn,
} from "../lib/ssrf-fetch";

type ServerHandler = http.RequestListener;

const loopbackLookup: LookupFn = async () => [{ address: "127.0.0.1", family: 4 as const }];

async function withServers(
  handlerFactories: Array<(ports: number[]) => ServerHandler>,
  fn: (ports: number[]) => Promise<void>
): Promise<void> {
  const servers: http.Server[] = [];
  try {
    for (let i = 0; i < handlerFactories.length; i++) {
      const server = http.createServer(() => undefined);
      await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
      servers.push(server);
    }
    const ports = servers.map((s) => (s.address() as AddressInfo).port);
    handlerFactories.forEach((factory, i) => {
      const server = servers[i];
      if (!server) return;
      server.removeAllListeners("request");
      server.on("request", factory(ports));
    });
    await fn(ports);
  } finally {
    await Promise.all(servers.map((s) => serverClose(s)));
  }
}

function serverClose(server: http.Server): Promise<void> {
  return new Promise((resolve) => server.close(() => resolve()));
}

describe("ssrfFetch", () => {
  it("fetches content from a pinned connection", async () => {
    await withServers(
      [
        () =>
          (_req, res) => {
            res.end("hello from origin");
          },
      ],
      async ([port]) => {
        const res = await ssrfFetch(`http://127.0.0.1:${port}/`, {
          lookup: loopbackLookup,
          allowPrivateForTest: true,
        });
        expect(res.status).toBe(200);
        expect(await res.text()).toBe("hello from origin");
      }
    );
  });

  it("rejects mixed public/private DNS answers before connecting", async () => {
    const mixedLookup: LookupFn = async () => [
      { address: "93.184.216.34", family: 4 as const },
      { address: "192.168.1.1", family: 4 as const },
    ];
    await expect(
      ssrfFetch("https://mixed.example.com/", { lookup: mixedLookup })
    ).rejects.toBeInstanceOf(SsrfBlockedError);
  });

  it("rejects hostnames that resolve only to private addresses", async () => {
    const privateLookup: LookupFn = async () => [{ address: "10.0.0.5", family: 4 as const }];
    await expect(
      ssrfFetch("https://internal.example.com/", { lookup: privateLookup })
    ).rejects.toBeInstanceOf(SsrfBlockedError);
  });

  it("rejects credentials in the URL", async () => {
    await expect(
      ssrfFetch("https://user:pass@example.com/", { lookup: loopbackLookup })
    ).rejects.toBeInstanceOf(SsrfBlockedError);
  });

  it("rejects credentials in a redirect target", async () => {
    await withServers(
      [
        () =>
          (_req, res) => {
            res.writeHead(302, { Location: "https://user:pass@evil.example.com/" });
            res.end();
          },
      ],
      async ([port]) => {
        await expect(
          ssrfFetch(`http://127.0.0.1:${port}/`, {
            lookup: loopbackLookup,
            allowPrivateForTest: true,
          })
        ).rejects.toBeInstanceOf(SsrfBlockedError);
      }
    );
  });

  it("rejects redirects to non-HTTP schemes", async () => {
    await withServers(
      [
        () =>
          (_req, res) => {
            res.writeHead(302, { Location: "file:///etc/passwd" });
            res.end();
          },
      ],
      async ([port]) => {
        await expect(
          ssrfFetch(`http://127.0.0.1:${port}/`, {
            lookup: loopbackLookup,
            allowPrivateForTest: true,
          })
        ).rejects.toBeInstanceOf(SsrfBlockedError);
      }
    );
  });

  it("rejects redirect loops after the configured maximum", async () => {
    await withServers(
      [
        () =>
          (_req, res) => {
            res.writeHead(302, { Location: "/loop" });
            res.end("loop");
          },
      ],
      async ([port]) => {
        await expect(
          ssrfFetch(`http://127.0.0.1:${port}/loop`, {
            lookup: loopbackLookup,
            allowPrivateForTest: true,
            maxRedirects: 3,
          })
        ).rejects.toBeInstanceOf(SsrfBlockedError);
      }
    );
  });

  it("strips sensitive headers on cross-origin redirects", async () => {
    await withServers(
      [
        (ports) =>
          (_req, res) => {
            res.writeHead(302, { Location: `http://127.0.0.1:${ports[1]}/final` });
            res.end();
          },
        () =>
          (req, res) => {
            res.end(JSON.stringify({ auth: req.headers.authorization ?? null }));
          },
      ],
      async ([portA]) => {
        const res = await ssrfFetch(`http://127.0.0.1:${portA}/redirect`, {
          lookup: loopbackLookup,
          allowPrivateForTest: true,
          headers: { Authorization: "Bearer secret" },
        });
        const body = (await res.json()) as { auth: string | null };
        expect(body.auth).toBeNull();
      }
    );
  });

  it("keeps the Authorization header on same-origin redirects", async () => {
    await withServers(
      [
        () =>
          (req, res) => {
            if (req.url === "/redirect") {
              res.writeHead(302, { Location: "/final" });
              res.end();
              return;
            }
            res.end(JSON.stringify({ auth: req.headers.authorization ?? null }));
          },
      ],
      async ([port]) => {
        const res = await ssrfFetch(`http://127.0.0.1:${port}/redirect`, {
          lookup: loopbackLookup,
          allowPrivateForTest: true,
          headers: { Authorization: "Bearer secret" },
        });
        const body = (await res.json()) as { auth: string | null };
        expect(body.auth).toBe("Bearer secret");
      }
    );
  });

  it("sends POST bodies to the redirected endpoint on 307/308", async () => {
    await withServers(
      [
        (ports) =>
          (_req, res) => {
            res.writeHead(307, { Location: `http://127.0.0.1:${ports[1]}/final` });
            res.end();
          },
        () =>
          async (req, res) => {
            const chunks: Buffer[] = [];
            for await (const chunk of req) chunks.push(chunk as Buffer);
            res.end(Buffer.concat(chunks).toString());
          },
      ],
      async ([port]) => {
        const res = await ssrfFetch(`http://127.0.0.1:${port}/redirect`, {
          lookup: loopbackLookup,
          allowPrivateForTest: true,
          method: "POST",
          body: "payload",
        });
        expect(await res.text()).toBe("payload");
      }
    );
  });

  it("downgrades POST to GET on 302 across origins", async () => {
    await withServers(
      [
        (ports) =>
          (_req, res) => {
            res.writeHead(302, { Location: `http://127.0.0.1:${ports[1]}/final` });
            res.end();
          },
        () =>
          (req, res) => {
            res.end(req.method ?? "");
          },
      ],
      async ([port]) => {
        const res = await ssrfFetch(`http://127.0.0.1:${port}/redirect`, {
          lookup: loopbackLookup,
          allowPrivateForTest: true,
          method: "POST",
          body: "payload",
        });
        expect(await res.text()).toBe("GET");
      }
    );
  });
});

describe("resolvePinnedAddress", () => {
  it("rejects hostnames with any private answer", async () => {
    const lookup: LookupFn = async () => [
      { address: "93.184.216.34", family: 4 as const },
      { address: "10.0.0.5", family: 4 as const },
    ];
    await expect(resolvePinnedAddress("mixed.example.com", lookup)).rejects.toBeInstanceOf(
      SsrfBlockedError
    );
  });

  it("rejects hostnames with no DNS answers", async () => {
    const lookup: LookupFn = async () => [];
    await expect(resolvePinnedAddress("empty.example.com", lookup)).rejects.toBeInstanceOf(
      SsrfBlockedError
    );
  });

  it("rejects IPv4-mapped IPv6 answers", async () => {
    const lookup: LookupFn = async () => [{ address: "::ffff:127.0.0.1", family: 6 as const }];
    await expect(resolvePinnedAddress("rebind.example.com", lookup)).rejects.toBeInstanceOf(
      SsrfBlockedError
    );
  });
});
