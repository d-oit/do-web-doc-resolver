# Stitch Design Spec — do-web-doc-resolover

> Google Stitch screen definitions for the resolver workspace PWA.
> Stitch reads this file + `tokens/semantic.json` to generate pixel-consistent Next.js pages.

## Metadata

```yaml
name: do-web-doc-resolover
version: 1.0.0
tokens: tokens/semantic.json
output: app/
framework: Next.js 14 (App Router)
responsive: container-query
darkMode: data-theme attribute
```

## CLI Usage

```bash
stitch generate \
  --design cli/ui/stitch/DESIGN.md \
  --tokens cli/ui/tokens/semantic.json \
  --out app/
```

Options:
- `--dark` — also emit dark-mode variants
- `--breakpoints sm,md,lg,xl` — container query breakpoints (default: 320,640,1024,1440)
- `--a11y` — emit WCAG 2.2 AA annotation comments
- `--dry-run` — print generated structure without writing files

## Token Reference

All color and spacing values resolve from `tokens/semantic.json`. Components reference semantic tokens, never primitives.

### Surface Tokens

| Token | Description |
|---|---|
| `surface.bg` | Primary background |
| `surface.bg-elevated` | Cards, popovers, modals |
| `surface.bg-sunken` | Inputs, code blocks |
| `surface.bg-overlay` | Modal backdrop |

### Text Tokens

| Token | Description |
|---|---|
| `text.primary` | Primary body text |
| `text.secondary` | Labels, metadata |
| `text.tertiary` | Disabled, decorative |
| `text.inverse` | Text on dark surfaces |
| `text.link` | Interactive links |

### Interactive Tokens

| Token | Description |
|---|---|
| `interactive.bg` | Primary button/action bg |
| `interactive.bg-hover` | Hover state |
| `interactive.bg-active` | Pressed state |
| `interactive.bg-disabled` | Disabled state |
| `interactive.text` | Text on interactive bg |
| `interactive.border` | Interactive borders |
| `interactive.border-focus` | Focus rings |

### Signal Tokens

| Token | Description |
|---|---|
| `signal.success` | Success state |
| `signal.warning` | Warning state |
| `signal.error` | Error state |
| `signal.info` | Informational |

### Pipeline Tokens

| Token | Description |
|---|---|
| `pipeline.pending` | Queued step |
| `pipeline.running` | Active step |
| `pipeline.streaming` | SSE data flowing |
| `pipeline.complete` | Finished step |
| `pipeline.failed` | Failed step |

### Data Tokens

| Token | Description |
|---|---|
| `data.row-hover` | Table row hover |
| `data.row-selected` | Selected row |
| `data.row-stripe` | Alternating row |

### Spacing

| Token | Value |
|---|---|
| `--wdr-space-1` | 4px |
| `--wdr-space-2` | 8px |
| `--wdr-space-3` | 12px |
| `--wdr-space-4` | 16px |
| `--wdr-space-6` | 24px |
| `--wdr-space-8` | 32px |

### Breakpoints

| Name | Container Width |
|---|---|
| `sm` | >= 320px |
| `md` | >= 640px |
| `lg` | >= 1024px |
| `xl` | >= 1440px |

## Available Components

Components are pure CSS with BEM naming. All live in `components/`.

| Component | CSS Class | Description |
|---|---|---|
| App Shell | `.wdr-app` | Sidebar + main workspace. Source: `layouts/responsive.css` |
| Sidebar | `.wdr-sidebar` | Left navigation. Variants: expanded, collapsed |
| Bottom Nav | `.wdr-bottom-nav` | Mobile bottom bar (< 768px) |
| Icon Rail | `.wdr-icon-rail` | Tablet collapsed sidebar (768-1024px) |
| Button | `.wdr-button` | Actions. Variants: primary, secondary, ghost, danger, icon |
| Input | `.wdr-input` | Text entry. Variants: text, search, URL, select, textarea |
| DataTable | `.wdr-datatable` | Data tables. Variants: default, dense, compact |
| KeyValue | `.wdr-kv` | Metadata pair display. Variants: default, dense, striped |
| MarkdownViewer | `.wdr-markdown-viewer` | Rendered markdown pane |
| CodeBlock | `.wdr-codeblock` | Syntax-highlighted code |
| Stepper | `.wdr-stepper` | Pipeline cascade. States: pending, running, streaming, complete, failed |
| Progress | `.wdr-progress` | Progress bars. Variants: sm/md/lg, determinate/indeterminate |
| StreamIndicator | `.wdr-stream-indicator` | SSE connection status |
| Card | `.wdr-card` | Content container. Variants: default, interactive, flat, compact |
| Panel | `.wdr-panel` | Split pane layout. Variants: horizontal, vertical, collapsible |
| Modal | `.wdr-modal` | Dialog overlay. Variants: sm/md/lg, confirmation |
| Badge | `.wdr-badge` | Status indicator. Variants: success, warning, error, info, provider |
| Tooltip | `.wdr-tooltip` | Hover/focus info. Positions: top, bottom, left, right |

---

## Screen 1: Resolver Workspace

**Route:** `/`
**Epic:** #72 — Resolver Workspace Core View
**Issues:** #79, #80, #81, #82, #83

Main resolution screen. Command input, profile selector, pipeline progress, markdown output, and telemetry in a single workspace layout.

### Composition Tree

```
AppShell (wdr-app)
├── Sidebar (wdr-sidebar) -- expanded, lg+
│   ├── Nav section: Workspace (active)
│   ├── Nav section: Providers
│   ├── Nav section: History
│   └── Nav section: Settings
├── BottomNav (wdr-bottom-nav) -- < md
├── IconRail (wdr-icon-rail) -- md to lg
└── Main Content
    ├── CommandBar (panel header area)
    │   ├── Input (wdr-input--search, lg size)
    │   │   └── placeholder: "Enter URL or query..."
    │   ├── ProfileSelector (wdr-button--secondary)
    │   │   └── label: "Fast" | "Balanced" | "Quality"
    │   └── Button (wdr-button--primary)
    │       └── label: "Resolve", icon: arrow-right
    └── WorkspaceSplit (wdr-panel--horizontal)
        ├── InputPane (wdr-panel__left)
        │   ├── Card (wdr-card--flat)
        │   │   ├── Card Header
        │   │   │   ├── Badge (wdr-badge--info) "Input"
        │   │   │   └── KeyValue (wdr-kv--dense)
    │   │   │       ├── Source: [resolved URL]
    │   │   │       ├── Profile: [selected profile]
    │   │   │       └── Cache: miss | hit
    │   │   └── Card Body
    │   │       ├── Stepper (wdr-stepper--vertical)
    │   │       │   ├── Step 1: exa_mcp -- state: pending | running | complete | failed
    │   │       │   ├── Step 2: exa -- state: pending | running | complete | failed
    │   │       │   ├── Step 3: tavily -- state: pending | running | complete | failed
    │   │       │   └── Step 4: duckduckgo -- state: pending | running | complete | failed
    │   │       └── StreamIndicator
    │   │           └── state: disconnected | connecting | streaming | complete | error
    │   └── OutputPane (wdr-panel__right)
    │       ├── Card (wdr-card--default)
    │       │   ├── Card Header
    │       │   │   ├── Badge (wdr-badge--success) "Result"
    │       │   │   ├── Button (wdr-button--ghost, icon: copy)
    │       │   │   └── Button (wdr-button--ghost, icon: download)
    │       │   └── Card Body
    │       │       └── MarkdownViewer (wdr-markdown-viewer)
    │       │           └── rendered content with code blocks, tables, links
    │       └── Card (wdr-card--compact)
    │           └── Card Body
    │               └── KeyValue (wdr-kv--striped)
    │                   ├── Provider: [active provider]
    │                   ├── Latency: [ms]
    │                   ├── Tokens: [count]
    │                   ├── Cache: hit | miss
    │                   └── Profile: [fast | balanced | quality]
    └── TelemetryAccordion (collapsible panel)
        ├── Header: "Telemetry Trace"
        ├── Progress (wdr-progress--multi-segment)
        │   ├── Segment: exa_mcp (color: pipeline.running)
        │   ├── Segment: exa (color: pipeline.pending)
        │   ├── Segment: tavily (color: pipeline.pending)
        │   └── Segment: duckduckgo (color: pipeline.pending)
        └── DataTable (wdr-datatable--dense)
            ├── Columns: Provider | Status | Latency | Tokens | Error
            └── Rows: one per cascade step
```

### Layout Tokens

```yaml
layout:
  type: app-shell-split
  sidebar:
    width: 16rem
    bg: surface.bg
    border: border.default
    collapsed-width: 3rem          # icon-rail mode
  command-bar:
    height: 56px
    bg: surface.bg-elevated
    border-bottom: border.default
    padding: 0 var(--wdr-space-4)
    gap: var(--wdr-space-3)
  workspace-split:
    type: horizontal
    ratio: 40:60
    resizable: true
    min-left: 280px
    min-right: 400px
  input-pane:
    bg: surface.bg
    padding: var(--wdr-space-4)
  output-pane:
    bg: surface.bg
    padding: var(--wdr-space-4)
  telemetry:
    height: auto
    max-height: 240px
    bg: surface.bg-sunken
    border-top: border.default
    padding: var(--wdr-space-3)
```

### Interaction States

```yaml
command-input:
  default:
    bg: surface.bg-sunken
    border: border.default
    text: text.primary
    placeholder: text.tertiary
  focus:
    border: interactive.border-focus
    outline: 2px solid interactive.border-focus
    outline-offset: 2px
  error:
    border: signal.error
    text: text.primary

profile-selector:
  default:
    bg: surface.bg-elevated
    border: border.default
    text: text.primary
  active:
    bg: interactive.bg
    text: interactive.text
  hover:
    bg: surface.bg-sunken

resolve-button:
  default:
    bg: interactive.bg
    text: interactive.text
  hover:
    bg: interactive.bg-hover
  active:
    bg: interactive.bg-active
  disabled:
    bg: interactive.bg-disabled
    text: text.tertiary
  loading:
    bg: interactive.bg
    animation: pulse-stream 1.5s ease infinite

stepper-step:
  pending:
    icon-color: pipeline.pending
    label-color: text.tertiary
  running:
    icon-color: pipeline.running
    label-color: text.primary
    animation: pulse-stream 1.5s ease infinite
  streaming:
    icon-color: pipeline.streaming
    label-color: text.primary
  complete:
    icon-color: pipeline.complete
    label-color: text.primary
  failed:
    icon-color: pipeline.failed
    label-color: signal.error

output-pane:
  loading:
    shimmer: wdr-shimmer animation
    duration: 1.5s
  loaded:
    transition: opacity 200ms ease-out

datatable-row:
  default:
    bg: transparent
    border-bottom: border.subtle
  hover:
    bg: data.row-hover
  selected:
    bg: data.row-selected
```

### Responsive Behavior

```yaml
sm (< 640px):
  sidebar: hidden
  bottom-nav: visible
  workspace-split: vertical stack
  command-bar: single row, input fills width, button below
  telemetry: collapsed by default

md (640-1024px):
  sidebar: hidden
  icon-rail: visible (3rem, icons only)
  workspace-split: horizontal 35:65
  command-bar: single row
  telemetry: collapsed by default

lg (1024-1440px):
  sidebar: expanded (16rem)
  workspace-split: horizontal 40:60, resizable
  command-bar: single row with all controls
  telemetry: collapsible, default collapsed

xl (>= 1440px):
  sidebar: expanded (16rem)
  workspace-split: horizontal 35:65, resizable
  command-bar: single row with all controls
  telemetry: collapsible, default expanded
```

---

## Screen 2: Provider Settings

**Route:** `/settings/providers`
**Epic:** #73 — BYOK API Key Management & Security
**Issues:** #84, #85, #86

BYOK (Bring Your Own Key) management. Masked inputs for API keys, provider health checks, connection testing.

### Composition Tree

```
AppShell (wdr-app)
├── Sidebar (wdr-sidebar) -- expanded
│   ├── Nav section: Workspace
│   ├── Nav section: Providers
│   ├── Nav section: History
│   └── Nav section: Settings (active)
└── Main Content
    ├── PageHeader
    │   ├── Heading (h1): "Provider Settings"
    │   └── Badge (wdr-badge--info) "BYOK"
    └── ProviderGrid (CSS Grid, auto-fill, min 320px)
        ├── Card (wdr-card--outlined) -- per provider
        │   ├── Card Header
        │   │   ├── Badge (wdr-badge--provider) -- provider name
        │   │   │   variants: exa, tavily, firecrawl, mistral, jina
        │   │   ├── StatusBadge
        │   │   │   connected: wdr-badge--success
        │   │   │   disconnected: wdr-badge--warning
        │   │   │   error: wdr-badge--error
        │   │   └── Tooltip (wdr-tooltip)
        │   │       └── last checked: [timestamp]
        │   ├── Card Body
        │   │   ├── Label: "API Key"
        │   │   ├── Input (wdr-input--password, masked)
        │   │   │   ├── default: masked "●●●●●●●●●●●●●●●●"
        │   │   │   ├── focus: reveal toggle visible
        │   │   │   └── edit: clear, paste, type
        │   │   ├── KeyValue (wdr-kv--dense)
        │   │   │   ├── Rate Limit: [n]/min
        │   │   │   ├── Tier: free | pro | enterprise
        │   │   │   └── Endpoint: [url]
        │   │   └── Button (wdr-button--secondary)
        │   │       └── label: "Test Connection"
        │   └── Card Footer
        │       ├── Button (wdr-button--ghost--danger) "Remove"
        │       └── Button (wdr-button--primary) "Save"
        │
        └── Card (wdr-card--flat) -- "Add Provider" card
            ├── Card Body
            │   ├── Button (wdr-button--ghost, icon: plus)
            │   │   └── label: "Add Provider"
            │   └── Input (wdr-input--select)
            │       └── options: exa, tavily, firecrawl, mistral, jina
```

### Layout Tokens

```yaml
layout:
  type: page-scroll
  page-header:
    padding: var(--wdr-space-6) var(--wdr-space-4)
    bg: surface.bg
    border-bottom: border.default
  provider-grid:
    display: grid
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr))
    gap: var(--wdr-space-4)
    padding: var(--wdr-space-4)
  provider-card:
    bg: surface.bg-elevated
    border: 1px solid border.default
    border-radius: 8px
    padding: 0
    status-accent: left border 3px
      connected: signal.success
      disconnected: signal.warning
      error: signal.error
```

### Interaction States

```yaml
key-input:
  masked:
    bg: surface.bg-sunken
    text: text.tertiary
    font: monospace
    value: "●●●●●●●●●●●●●●●●"
  revealed:
    bg: surface.bg-sunken
    text: text.primary
    font: monospace
  focus:
    border: interactive.border-focus
    reveal-toggle: visible (icon: eye / eye-off)
  editing:
    bg: surface.bg
    border: interactive.border
    clear-button: visible (icon: x)
  error:
    border: signal.error
    helper-text: signal.error color

test-connection:
  idle:
    bg: surface.bg-elevated
    text: text.primary
    border: border.default
  testing:
    bg: surface.bg-elevated
    text: text.secondary
    progress: wdr-progress--indeterminate
    button: disabled, label "Testing..."
  success:
    bg: surface.bg-elevated
    border-left: 3px solid signal.success
    badge: wdr-badge--success "Connected"
    latency: displayed in KeyValue
  failure:
    bg: surface.bg-elevated
    border-left: 3px solid signal.error
    badge: wdr-badge--error "Failed"
    error-message: displayed below input

provider-badge:
  exa:
    bg: oklch(0.55 0.15 200)
    text: text.inverse
  tavily:
    bg: oklch(0.60 0.12 280)
    text: text.inverse
  firecrawl:
    bg: oklch(0.55 0.15 30)
    text: text.inverse
  mistral:
    bg: oklch(0.50 0.10 260)
    text: text.inverse
  jina:
    bg: oklch(0.65 0.14 155)
    text: text.inverse

save-button:
  default:
    disabled: true (no changes)
  dirty:
    bg: interactive.bg
    text: interactive.text
    enabled: true
  saving:
    bg: interactive.bg
    animation: pulse-stream
    disabled: true
  saved:
    bg: signal.success
    text: text.inverse
    duration: 2000ms then revert
```

### Responsive Behavior

```yaml
sm (< 640px):
  provider-grid: single column
  cards: full width
  key-input: full width
  card-actions: stacked vertical

md (640-1024px):
  provider-grid: 2 columns
  cards: equal width
  card-actions: horizontal row

lg (>= 1024px):
  provider-grid: auto-fill, minmax(320px, 1fr)
  cards: fluid width
  card-actions: horizontal row
```

---

## Screen 3: History Browser

**Route:** `/history`
**Epic:** #74 — History & Semantic Cache UI
**Issues:** #88, #89, #90, #91

Browse past resolutions. Sortable data table with search/filter. Restore from cache for instant loads.

### Composition Tree

```
AppShell (wdr-app)
├── Sidebar (wdr-sidebar) -- expanded
│   ├── Nav section: Workspace
│   ├── Nav section: Providers
│   ├── Nav section: History (active)
│   └── Nav section: Settings
├── BottomNav (wdr-bottom-nav) -- < md
├── IconRail (wdr-icon-rail) -- md to lg
└── Main Content
    ├── PageHeader
    │   ├── Heading (h1): "History"
    │   ├── Input (wdr-input--search)
    │   │   └── placeholder: "Search history..."
    │   └── FilterBar
    │       ├── Input (wdr-input--select) -- "Date Range"
    │       │   └── options: Today | 7d | 30d | All
    │       ├── Input (wdr-input--select) -- "Profile"
    │       │   └── options: All | Fast | Balanced | Quality
    │       └── Input (wdr-input--select) -- "Provider"
    │           └── options: All | exa | tavily | duckduckgo | ...
    ├── DataTable (wdr-datatable--default, lg; wdr-datatable--dense, sm/md)
    │   ├── Columns (sortable)
    │   │   ├── Timestamp (default sort: desc)
    │   │   ├── Input (URL or query, truncated)
    │   │   ├── Profile
    │   │   ├── Provider
    │   │   ├── Status (badge column)
    │   │   ├── Latency
    │   │   └── Actions
    │   ├── Row
    │   │   ├── Cell: 2026-03-20 14:32
    │   │   ├── Cell: "https://react.dev/reference/react/..."
    │   │   ├── Cell: Balanced
    │   │   ├── Cell: Badge (wdr-badge--provider) "exa"
    │   │   ├── Cell: Badge (wdr-badge--success) "Cached"
    │   │   ├── Cell: 342ms
    │   │   └── Cell:
    │   │       ├── Button (wdr-button--ghost, icon: arrow-right)
    │   │       │   └── tooltip: "Restore from cache"
    │   │       ├── Button (wdr-button--ghost, icon: copy)
    │   │       │   └── tooltip: "Copy result"
    │   │       └── Button (wdr-button--ghost--danger, icon: trash)
    │   │           └── tooltip: "Delete"
    │   └── EmptyState (when no results)
    │       └── Card (wdr-card--flat)
    │           └── Card Body
    │               ├── Heading: "No history entries"
    │               └── Text: "Resolved queries appear here."
    └── Pagination (below table)
        ├── Button (wdr-button--ghost) "Previous" -- disabled on page 1
        ├── Text: "Page 1 of 12"
        └── Button (wdr-button--ghost) "Next"
```

### Layout Tokens

```yaml
layout:
  type: page-scroll
  page-header:
    padding: var(--wdr-space-6) var(--wdr-space-4)
    bg: surface.bg
    border-bottom: border.default
    gap: var(--wdr-space-3)
    flex-direction: column
  filter-bar:
    display: flex
    gap: var(--wdr-space-2)
    flex-wrap: wrap
  datatable-container:
    padding: var(--wdr-space-4)
    overflow-x: auto
  pagination:
    padding: var(--wdr-space-3) var(--wdr-space-4)
    display: flex
    justify-content: space-between
    align-items: center
    border-top: border.default
```

### Interaction States

```yaml
search-input:
  default:
    bg: surface.bg-sunken
    border: border.default
    text: text.primary
    placeholder: text.tertiary
  focus:
    border: interactive.border-focus
    outline: 2px solid interactive.border-focus
  with-value:
    clear-button: visible (icon: x)

filter-select:
  default:
    bg: surface.bg-elevated
    border: border.default
    text: text.primary
  active:
    bg: surface.bg-elevated
    border: interactive.border
    badge: wdr-badge--info (filter count)
  open:
    bg: surface.bg-elevated
    border: interactive.border-focus
    dropdown: surface.bg-elevated, shadow, z-modal

column-header:
  default:
    bg: surface.bg-sunken
    text: text.secondary
    font: uppercase, label style
    cursor: pointer
  hover:
    bg: data.row-hover
    text: text.primary
  sorted-asc:
    text: text.primary
    icon: chevron-up
  sorted-desc:
    text: text.primary
    icon: chevron-down

restore-button:
  default:
    bg: transparent
    text: text.secondary
    icon: arrow-right
  hover:
    bg: data.row-hover
    text: interactive.bg
    icon: arrow-right
  restoring:
    bg: interactive.bg
    text: interactive.text
    animation: pulse-stream
    disabled: true

empty-state:
  bg: surface.bg
  text: text.tertiary
  padding: var(--wdr-space-8)
  text-align: center
```

### Mobile Behavior (sm)

```yaml
sm (< 640px):
  page-header:
    heading: h2 (smaller)
    search: full width
    filter-bar: horizontal scroll (overflow-x: auto)
  datatable:
    variant: wdr-datatable--dense
    columns-visible: Timestamp | Input | Status | Actions
    columns-hidden: Profile | Provider | Latency
    scrollable: horizontal overflow
  row:
    height: var(--wdr-dense-row, 20px)
  pagination:
    simplified: "< Page X >" only

md (640-1024px):
  datatable:
    variant: wdr-datatable--dense
    columns-visible: all
  filter-bar: flex-wrap
```

---

## Screen 4: Error States

**Route:** N/A (overlays / inline states across screens)
**Epic:** #72, #73
**Issues:** #81, #83, #86

Error state compositions for pipeline failures, rate limiting, network errors, and provider unavailability. These are not standalone routes but inline/overlay states rendered within other screens.

### 4A: Failed Pipeline

Triggered when all cascade steps fail.

```
Card (wdr-card--status-accented, accent: signal.error)
├── Card Header
│   ├── Badge (wdr-badge--error) "Pipeline Failed"
│   └── Button (wdr-button--ghost, icon: x) -- dismiss
├── Card Body
│   ├── Stepper (wdr-stepper--vertical)
│   │   ├── Step: exa_mcp -- state: failed
│   │   │   └── KeyValue (wdr-kv--dense)
│   │   │       ├── Error: "API key invalid"
│   │   │       └── Code: 401
│   │   ├── Step: exa -- state: failed
│   │   │   └── KeyValue (wdr-kv--dense)
│   │   │       ├── Error: "Rate limit exceeded"
│   │   │       └── Code: 429
│   │   ├── Step: tavily -- state: failed
│   │   │   └── KeyValue (wdr-kv--dense)
│   │   │       ├── Error: "Timeout (30s)"
│   │   │       └── Code: 504
│   │   └── Step: duckduckgo -- state: failed
│   │       └── KeyValue (wdr-kv--dense)
│   │           ├── Error: "Connection refused"
│   │           └── Code: 503
│   └── KeyValue (wdr-kv--striped)
│       ├── Total Duration: [ms]
│       └── Attempted: 4 / 4 providers
└── Card Footer
    ├── Button (wdr-button--primary) "Retry All"
    ├── Button (wdr-button--secondary) "Retry Failed Only"
    └── Button (wdr-button--ghost) "View Logs"
```

**Tokens:**

```yaml
failed-pipeline:
  card-accent: signal.error
  badge-bg: signal.error
  badge-text: text.inverse
  stepper-icon: pipeline.failed
  error-text: signal.error
  code-text: text.tertiary
  bg: surface.bg-elevated
  retry-button:
    bg: interactive.bg
    hover: interactive.bg-hover
```

### 4B: Rate Limited

Triggered when a provider returns HTTP 429.

```
Card (wdr-card--status-accented, accent: signal.warning)
├── Card Header
│   ├── Badge (wdr-badge--warning) "Rate Limited"
│   └── Text: provider name
├── Card Body
│   ├── KeyValue (wdr-kv--dense)
│   │   ├── Provider: [name]
│   │   ├── Limit: [n] requests / [period]
│   │   ├── Remaining: 0
│   │   ├── Retry-After: [seconds]
│   │   └── Reset: [timestamp]
│   └── Progress (wdr-progress--determinate)
│       └── value: countdown to reset
└── Card Footer
    ├── Button (wdr-button--primary) "Retry in [n]s" -- disabled until reset
    └── Button (wdr-button--secondary) "Skip Provider"
```

**Tokens:**

```yaml
rate-limited:
  card-accent: signal.warning
  badge-bg: signal.warning
  badge-text: text.inverse
  countdown-progress:
    track: surface.bg-sunken
    fill: signal.warning
    height: 4px
  retry-button:
    disabled: true
    countdown-text: text.secondary
  bg: surface.bg-elevated
```

### 4C: Network Error

Triggered on fetch failure, DNS error, or timeout.

```
Card (wdr-card--status-accented, accent: signal.error)
├── Card Header
│   └── Badge (wdr-badge--error) "Network Error"
├── Card Body
│   ├── KeyValue (wdr-kv--dense)
│   │   ├── Type: DNS | Timeout | Connection Reset | TLS
│   │   ├── Endpoint: [url]
│   │   ├── Duration: [ms] (before failure)
│   │   └── Timestamp: [iso datetime]
│   └── CodeBlock (wdr-codeblock)
│       └── raw error output (truncated, expandable)
└── Card Footer
    ├── Button (wdr-button--primary) "Retry"
    ├── Button (wdr-button--ghost) "Copy Error"
    └── Button (wdr-button--ghost) "Report Issue"
```

**Tokens:**

```yaml
network-error:
  card-accent: signal.error
  badge-bg: signal.error
  badge-text: text.inverse
  codeblock:
    bg: surface.bg-sunken
    text: text.primary
    border: border.subtle
    max-height: 120px
    overflow: auto
    font: JetBrains Mono, 12px
  bg: surface.bg-elevated
```

### 4D: Provider Unavailable

Triggered when a specific provider health check fails or returns non-2xx.

```
Card (wdr-card--flat)
├── Card Header
│   ├── Badge (wdr-badge--provider) "[provider name]"
│   └── Badge (wdr-badge--error) "Unavailable"
├── Card Body
│   ├── KeyValue (wdr-kv--dense)
│   │   ├── Status: [HTTP status code]
│   │   ├── Response Time: timeout | [ms]
│   │   ├── Last Successful: [timestamp]
│   │   └── Consecutive Failures: [count]
│   └── Text (text.secondary)
│       └── "Provider may be experiencing an outage."
└── Card Footer
    ├── Button (wdr-button--secondary) "Test Connection"
    ├── Button (wdr-button--ghost) "View Status Page"
    └── Button (wdr-button--ghost--danger) "Disable Provider"
```

**Tokens:**

```yaml
provider-unavailable:
  provider-badge:
    exa: oklch(0.55 0.15 200)
    tavily: oklch(0.60 0.12 280)
    firecrawl: oklch(0.55 0.15 30)
    mistral: oklch(0.50 0.10 260)
    jina: oklch(0.65 0.14 155)
  status-badge: signal.error
  status-page-link:
    text: text.link
    hover: interactive.bg-hover
  bg: surface.bg-elevated
  border: border.subtle
```

### Error State Inline Behavior

Error states render inline within the parent screen, not as page navigations.

```yaml
placement:
  resolver-workspace:
    failed-pipeline: replaces output pane content
    rate-limited: inline below stepper step
    network-error: replaces output pane content
    provider-unavailable: inline below failed stepper step
  provider-settings:
    provider-unavailable: replaces test-connection success state
  history-browser:
    network-error: modal overlay (wdr-modal--sm)

animation:
  enter: opacity 0 -> 1, 200ms ease-out
  exit: opacity 1 -> 0, 150ms ease-in
  reduced-motion: none

z-index:
  inline-card: auto (in flow)
  modal-overlay: var(--wdr-z-overlay)
  modal-content: var(--wdr-z-modal)
```

---

## Dark Mode

All screens inherit dark mode via `tokens/semantic.json` remap under `[data-theme="dark"]`.

```yaml
dark-mode-override:
  surface.bg: oklch(0.15 0.01 230)
  surface.bg-elevated: oklch(0.18 0.01 230)
  surface.bg-sunken: oklch(0.12 0.01 230)
  text.primary: oklch(0.95 0.005 230)
  text.secondary: oklch(0.70 0.01 230)
  border.default: oklch(0.25 0.01 230)
  interactive.bg: oklch(0.57 0.10 230)
  data.row-hover: oklch(0.20 0.01 230)
  data.row-selected: oklch(0.22 0.02 230)
  data.row-stripe: oklch(0.17 0.005 230)
  shadows: oklch(0 0 0 / 0.4)
```

Stitch emits both light and dark CSS when `--dark` flag is passed. Components auto-switch via `var()` references — no per-component dark overrides needed.

## Accessibility

All screens must meet WCAG 2.2 AA:

- Focus-visible rings on all interactive elements (`2px solid interactive.border-focus`, offset `2px`)
- Skip navigation link on every screen
- `aria-live="polite"` on StreamIndicator, Progress, and status badges
- `aria-sort` on sortable DataTable columns
- `role="dialog"` + focus trap on Modal overlays
- Minimum 44x44px touch targets on mobile
- Reduced motion: disable all transitions/animations via `prefers-reduced-motion: reduce`
- Forced colors mode support via `forced-colors: active` media query

## Generated File Structure

Running `stitch generate` produces:

```
app/
├── layout.tsx                    # AppShell wrapper, theme provider
├── page.tsx                      # Screen 1: Resolver Workspace
├── settings/
│   └── providers/
│       └── page.tsx              # Screen 2: Provider Settings
├── history/
│   └── page.tsx                  # Screen 3: History Browser
└── components/
    ├── FailedPipeline.tsx        # Screen 4A
    ├── RateLimited.tsx           # Screen 4B
    ├── NetworkError.tsx          # Screen 4C
    └── ProviderUnavailable.tsx   # Screen 4D
```

Error state components are imported by parent screens where needed, not standalone routes.
