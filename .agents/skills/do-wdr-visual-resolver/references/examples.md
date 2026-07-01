# Usage Examples: Visual Resolver

## Example 1: Scanned Academic Paper

- **URL**: `https://archive.org/details/some-scanned-paper.pdf`
- **Query**: "Find the experimental results for the titanium alloy test"
- **Result**: `VisualResolver` renders the PDF, CLIP identifies the page with the relevant chart/table, and returns the OCR'd text of that specific area.

## Example 2: JS-Heavy Dashboard

- **URL**: `https://app.dashboard.io/metrics`
- **Query**: "What is the current uptime percentage?"
- **Result**: Standard extractors see a loading spinner or empty `<div>`. `VisualResolver` waits for rendering, sees the "99.98%" text in the uptime widget, and extracts it.

## Example 3: Infographic

- **URL**: `https://blog.com/state-of-the-market-infographic.jpg`
- **Query**: "Market share of electric vehicles in 2024"
- **Result**: CLIP matches the query to the visual representation of the pie chart in the infographic.
