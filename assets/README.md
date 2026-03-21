# Assets

Visual assets for documentation, README, and release notes.

## Folder Structure

```
assets/
├── screenshots/
│   ├── homepage.png              # Main UI screenshot
│   ├── help-page.png             # Help page screenshot
│   ├── homepage-full.png         # Full page capture
│   ├── homepage-annotated.png    # Annotated with element refs
│   ├── release-vX.Y.Z/          # Version-specific captures
│   │   ├── homepage.png
│   │   ├── help-page.png
│   │   └── ...
│   ├── flow-resolve/             # Resolution flow screenshots
│   │   ├── 01-homepage.png
│   │   ├── 02-enter-query.png
│   │   ├── 03-resolving.png
│   │   └── 04-result.png
│   └── responsive/               # Responsive screenshots
│       ├── desktop.png
│       ├── laptop.png
│       ├── tablet.png
│       └── mobile.png
└── README.md                     # This file
```

## Usage in Documentation

### README.md

```markdown
![Web Doc Resolver](./assets/screenshots/homepage.png)
```

### Release Notes

```markdown
## What's New in vX.Y.Z

![New Feature](./assets/screenshots/release-vX.Y.Z/new-feature.png)
```

## Generating Screenshots

### Quick Capture

```bash
# Capture homepage
./scripts/capture/capture-release.sh

# Capture with version
./scripts/capture/capture-release.sh 1.0.0

# Capture flow
./scripts/capture/capture-flow.sh resolve

# Capture responsive
./scripts/capture/capture-responsive.sh
```

### Using agent-browser directly

```bash
agent-browser open "https://web-eight-ivory-29.vercel.app"
agent-browser wait --load networkidle
agent-browser screenshot assets/screenshots/homepage.png
agent-browser close
```

## Screenshot Guidelines

1. **Consistent viewport**: Use 1280x720 for standard captures
2. **Wait for load**: Always use `wait --load networkidle`
3. **Version folders**: Use `release-vX.Y.Z/` for releases
4. **Naming**: Use kebab-case (e.g., `help-page.png`)
5. **Full page**: Use `--full` for documentation
6. **Annotated**: Use `--annotate` for UI docs

## Automation

Screenshots are captured:
- On every release (via `capture-release.sh`)
- In CI/CD pipeline (optional)
- On pre-commit if UI changes detected
