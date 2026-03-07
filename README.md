# web-doc-resolver

🔍 Resolve queries or URLs into compact, LLM-ready markdown using an intelligent, low-cost cascade.

## Overview

This agent skill implements a v4 cascade resolver that prioritizes free and low-cost data sources:

1. **llms.txt** - Check for structured LLM documentation first (free)
2. **Exa highlights** - Token-efficient query resolution using highlights (low-cost)
3. **Tavily** - Fallback for comprehensive search (configurable)
4. **Firecrawl** - Last resort for deep extraction (highest cost)

## Features

✅ **Cost-Optimized**: Free sources first, paid APIs only when necessary
✅ **Token-Efficient**: Uses Exa highlights to minimize token usage
✅ **Agent-Ready**: Compatible with [agentskills.io](https://agentskills.io/)
✅ **Flexible**: All API keys are optional - works with free defaults
✅ **Well-Tested**: Includes comprehensive test suite and CI/CD

## Installation

```bash
# Clone the repository
git clone https://github.com/d-oit/web-doc-resolver.git
cd web-doc-resolver

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Usage

```python
from scripts.resolve import resolve

# Resolve a URL
result = resolve("https://example.com")
print(result)

# Resolve a query
result = resolve("latest AI research papers")
print(result)
```

### With API Keys (Optional)

```bash
# Set environment variables for enhanced features
export EXA_API_KEY="your-exa-key"
export TAVILY_API_KEY="your-tavily-key"
export FIRECRAWL_API_KEY="your-firecrawl-key"
```

### Command Line

```bash
# Resolve a URL
python scripts/resolve.py "https://example.com"

# Resolve a query
python scripts/resolve.py "machine learning tutorials"
```

## How It Works

The v4 cascade follows this decision tree:

```
Input (URL or query)
    |
    ├─ Is URL? → Check llms.txt first
    │             ├─ Found? → Return structured content ✓
    │             └─ Not found? → Try Firecrawl (if available)
    │
    └─ Is query? → Use Exa highlights first
                   ├─ Success? → Return highlights ✓
                   └─ Failed? → Try Tavily fallback
                                └─ Return best available result
```

## Development

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=scripts tests/
```

### Linting

```bash
# Format code
black scripts/ tests/

# Check style
flake8 scripts/ tests/
```

## Repository Structure

```
web-doc-resolver/
├── SKILL.md              # Agent skill specification
├── AGENTS.md             # Agent usage documentation  
├── README.md             # This file
├── LICENSE               # MIT license
├── requirements.txt      # Python dependencies
├── scripts/
│   └── resolve.py        # Main resolver implementation
├── tests/
│   └── test_resolve.py   # Test suite
└── .github/
    └── workflows/
        └── ci.yml         # GitHub Actions CI/CD
```

## API Keys

All API keys are **optional**. The skill degrades gracefully:

- **No keys**: Uses llms.txt (free) for URLs
- **Exa key only**: Adds token-efficient query resolution  
- **All keys**: Full cascade with maximum capability

### Getting API Keys

- **Exa**: [exa.ai](https://exa.ai/) - 1,000 requests/month free
- **Tavily**: [tavily.com](https://tavily.com/) - Free tier available
- **Firecrawl**: [firecrawl.dev](https://firecrawl.dev/) - 500 credits (one-time), free

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Agent Skill Usage

This repository follows the [agentskills.io](https://agentskills.io/) specification. See [AGENTS.md](AGENTS.md) for detailed integration instructions.

## Troubleshooting

See [AGENTS.md](AGENTS.md#troubleshooting) for common issues and solutions.

## Related Files

- [`SKILL.md`](SKILL.md) - Full agent skill specification
- [`AGENTS.md`](AGENTS.md) - Agent usage and integration guide
