# Web Doc Resolver UI

A Next.js web interface for [do-web-doc-resolover](../README.md) — resolves queries and URLs into compact, LLM-ready markdown via a free-first provider cascade.

## Quick Start

```bash
npm install
npm run dev
```

The app runs at [http://localhost:3000](http://localhost:3000).

## Environment Variables

| Variable | Required | Description | Default |
|---|---|---|---|
| `EXA_API_KEY` | No | Exa SDK neural search | — |
| `TAVILY_API_KEY` | No | Tavily comprehensive search | — |
| `SERPER_API_KEY` | No | Google search via Serper (2500 free credits) | — |
| `FIRECRAWL_API_KEY` | No | Firecrawl deep extraction | — |
| `MISTRAL_API_KEY` | No | Mistral AI-powered fallback | — |
| `WEB_RESOLVER_MAX_CHARS` | No | Max characters in response | `8000` |
| `NEXT_PUBLIC_APP_URL` | No | Public URL of this app | — |

**Note**: All API keys are optional. The resolver works with free providers (Jina Reader, DuckDuckGo, direct fetch).

## Available Scripts

| Script | Description |
|---|---|
| `npm run dev` | Start dev server with hot reload |
| `npm run build` | Production build |
| `npm start` | Start production server |
| `npm run lint` | Run ESLint |
| `npm run typecheck` | TypeScript type checking |
| `npm run test` | Run unit tests (Vitest) |
| `npm run test:watch` | Run tests in watch mode |
| `npm run test:coverage` | Run tests with coverage |
| `npm run test:e2e` | Run Playwright E2E tests |
| `npm run test:e2e:ui` | Run Playwright tests with UI |

## Tech Stack

- **Next.js 15** — App Router, server components
- **React 19** — UI framework
- **Tailwind CSS v4** — CSS-first configuration in `globals.css`
- **TypeScript** — strict mode
- **Vitest** — Unit testing
- **Playwright** — E2E testing
- **Vercel Speed Insights** — performance monitoring

## Deployment

Deployed via [Vercel](https://vercel.com):

```bash
cd web
vercel pull --yes
vercel build --prod
vercel deploy --prebuilt --prod
```

### Vercel Configuration

- **API Routes**: Configured with 60s max duration for long-running resolver operations
- **Security Headers**: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy
- **API Keys**: Should be marked as "Sensitive" in Vercel dashboard for security

## Project Structure

```
web/
├── app/
│   ├── layout.tsx        # Root layout (fonts, metadata, SpeedInsights)
│   ├── page.tsx          # Home page (resolver form)
│   ├── api/resolve/
│   │   └── route.ts      # API endpoint for resolution
│   ├── help/
│   │   └── page.tsx      # Help / FAQ page
│   └── globals.css       # Tailwind v4 config + theme tokens
├── tests/
│   ├── api/              # Unit tests (Vitest)
│   └── e2e/              # Playwright E2E tests
├── playwright.config.ts
├── vitest.config.ts
├── postcss.config.mjs
├── next.config.mjs
├── vercel.json
└── package.json
```
