# CLI Usage Reference

Complete usage reference for both the Python skill and the Rust `wdr` CLI.

## Python Skill (scripts/resolve.py)

### Synopsis

```bash
# Recommended (works with package imports):
python -m scripts.resolve <query_or_url> [OPTIONS]

# Installed via pip:
wdr <query_or_url> [OPTIONS]

# Legacy (only works if scripts/ has no package imports):
python scripts/resolve.py <query_or_url> [OPTIONS]
```

### Arguments

| Argument | Description |
|----------|------------|
| `query_or_url` | Search query string or full URL to resolve |

### Options

| Option | Description |
|--------|------------|
| `--skip <provider>` | Skip a provider (repeatable) |
| `--provider <name>` | Use only this provider |
| `--providers-order <list>` | Comma-separated custom cascade order |
| `--min-chars <n>` | Minimum chars for valid result (default: 200) |
| `--json` | Output result as JSON |

### Examples

```bash
# Basic query
python -m scripts.resolve "rust async book"

# Resolve a URL
python -m scripts.resolve "https://example.com"

# Skip paid providers
python -m scripts.resolve "query" --skip exa --skip tavily --skip mistral

# Skip Exa MCP, use SDK path
python -m scripts.resolve "query" --skip exa_mcp

# Custom provider order
python -m scripts.resolve "query" --providers-order "llms_txt,jina,direct_fetch"

# Single provider
python -m scripts.resolve "https://example.com" --provider jina

# JSON output
python -m scripts.resolve "query" --json
```

## Rust CLI (wdr)

### Synopsis

```bash
wdr [OPTIONS] <QUERY_OR_URL>
wdr resolve [OPTIONS] <QUERY_OR_URL>
wdr config [SUBCOMMAND]
```

### Global Options

| Flag | Short | Description |
|------|-------|------------|
| `--skip <name>` | `-s` | Skip provider (repeatable) |
| `--provider <name>` | `-p` | Use only this provider |
| `--providers-order <csv>` | `-P` | Override cascade order |
| `--min-chars <n>` | `-m` | Min chars threshold (default: 200) |
| `--json` | `-j` | JSON output to stdout |
| `--log-level <level>` | `-l` | Log level: error/warn/info/debug/trace |
| `--log-json` | | Structured JSON logs to stderr |
| `--config <path>` | `-c` | Path to config.toml |
| `--version` | `-V` | Print version |
| `--help` | `-h` | Print help |

### Subcommands

| Subcommand | Description |
|------------|------------|
| `resolve` | Resolve a query or URL (default) |
| `config show` | Print effective config (merged layers) |
| `config init` | Write default config.toml to current dir |
| `providers list` | List available providers and status |

### Examples

```bash
# Basic query
wdr "rust async book"

# Resolve URL
wdr resolve "https://example.com"

# Skip paid providers
wdr "query" --skip exa --skip tavily --skip mistral

# Custom cascade
wdr "query" --providers-order "llms_txt,jina,direct_fetch"

# JSON output
wdr "query" --json

# JSON structured logs
wdr "query" --log-json 2>run.log

# Show merged config
wdr config show

# List providers
wdr providers list

# Use custom config file
wdr --config ~/.config/wdr/config.toml "query"
```

## Output Format

### Default (plain text)
Resolved content is printed to **stdout**.
Log messages are printed to **stderr**.

### JSON (`--json`)

```json
{
  "source": "jina",
  "url": "https://example.com",
  "content": "...",
  "chars": 1234
}
```

### Error JSON (all providers failed)

```json
{
  "source": "none",
  "error": "No resolution method available"
}
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | All providers failed |
| 2 | Configuration error |
| 3 | Invalid arguments |
