# Contributing

Thanks for your interest in contributing!

## Ways to Contribute

- **Bug reports** - Open an issue with steps to reproduce
- **Feature requests** - Open an issue describing the use case
- **Documentation** - Fix typos, improve clarity, add examples
- **Code** - Bug fixes, new features, new plugins

## Development Setup

1. Fork and clone:
   ```bash
   git clone https://github.com/YOUR-USERNAME/kahl-dev-claude-marketplace.git
   cd kahl-dev-claude-marketplace
   ```

2. Install locally:
   ```bash
   ./scripts/install-local.sh
   ```

3. Make changes and test

## Code Style

### Python Scripts

- Use UV inline dependencies
- Use Click for CLI
- Support both human-readable and `--json` output
- Include `--help` documentation
- Handle errors gracefully with clear messages
- Use type hints

Example structure:
```python
#!/usr/bin/env python3
# /// script
# dependencies = ["httpx>=0.27.0", "click>=8.1.7"]
# ///

"""
Script description.

Usage:
    uv run script.py [options]
"""

import click

@click.command()
@click.option("--json", "output_json", is_flag=True, help="Output JSON")
def main(output_json: bool) -> None:
    """Command description."""
    pass

if __name__ == "__main__":
    main()
```

### SKILL.md

- Keep it concise (~800 tokens ideal)
- Use tables for quick reference
- Include common workflows
- Link to scripts, don't duplicate documentation

## Pull Request Process

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature
   ```

2. Make your changes

3. Test locally with Claude Code

4. Commit with clear message:
   ```bash
   git commit -m "✨ Add new feature X"
   ```

5. Push and create PR:
   ```bash
   git push origin feature/your-feature
   ```

6. Describe your changes in the PR

## Commit Message Conventions

Use emoji prefixes:
- ✨ New feature
- 🐛 Bug fix
- 📚 Documentation
- 🔧 Configuration
- 🎨 Code style/formatting
- ♻️ Refactoring
- 🔒 Security fix

## Adding a New Plugin

1. Create directory structure:
   ```
   plugins/your-plugin/
   ├── skills/
   │   └── your-skill/
   │       ├── SKILL.md
   │       └── scripts/
   ├── docs/
   └── README.md
   ```

2. Add to `marketplace.json`:
   ```json
   {
     "name": "your-plugin",
     "description": "...",
     "source": "./plugins/your-plugin",
     "keywords": ["..."],
     "license": "MIT"
   }
   ```

3. Update root README.md

## Questions?

Open an issue or reach out to [@kahl-dev](https://github.com/kahl-dev).
