import { fileURLToPath, URL } from "node:url";

const webRoot = fileURLToPath(new URL(".", import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  outputFileTracingRoot: webRoot,
  turbopack: { root: webRoot },
  images: {
    formats: ["image/avif", "image/webp"],
    // No remote hosts are allowlisted for the Next Image optimizer: the app
    // renders user-content images as plain <img> URLs client-side, so the
    // server-side optimizer never proxies arbitrary hosts. Add an explicit
    // protocol + hostname (never a wildcard) only when a product-required
    // asset host appears, with a rationale in web/README.md.
    remotePatterns: [],
  },
  reactStrictMode: true,
  poweredByHeader: false,
  headers: async () => [
    {
      source: "/:path*",
      headers: [
        {
          key: "Content-Security-Policy",
          value:
            "default-src 'self'; script-src 'self' 'unsafe-inline' https://va.vercel-scripts.com; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data: https:; font-src 'self' data:; connect-src 'self' https://vitals.vercel-insights.com; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; upgrade-insecure-requests;",
        },
        {
          key: "X-Content-Type-Options",
          value: "nosniff",
        },
        {
          key: "X-Frame-Options",
          value: "DENY",
        },
        {
          key: "Referrer-Policy",
          value: "strict-origin-when-cross-origin",
        },
      ],
    },
  ],
};

export default nextConfig;