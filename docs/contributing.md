# Contributing

## Quick Start

```bash
# Clone and setup
git clone <repo>
cd kahl-dev-claude-marketplace
make setup
```

## Adding a New Plugin

1. Create plugin structure:
   ```
   plugins/<name>/
   ├── .claude-plugin/
   │   └── plugin.json
   ├── skills/<skill-name>/
   │   ├── SKILL.md
   │   └── scripts/
   ├── docs/
   └── README.md
   ```

2. Register in `.claude-plugin/marketplace.json`:
   ```json
   {
     "name": "plugin-name",
     "description": "...",
     "source": "./plugins/plugin-name",
     "keywords": ["..."],
     "license": "MIT"
   }
   ```

3. Update root README.md

4. Update CHANGELOG.md under `[Unreleased]`

## Commit Conventions

Format: `<type>(<scope>): <description>`

```bash
feat(homeassistant): add new automation script
fix(homeassistant): correct entity validation
docs: update installation guide
chore(release): bump version to 1.1.0
```

**Types:** `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `style`, `perf`

## Version Bumping

```bash
make bump PLUGIN=homeassistant TYPE=patch  # 1.0.0 → 1.0.1
make bump PLUGIN=homeassistant TYPE=minor  # 1.0.0 → 1.1.0
make bump PLUGIN=homeassistant TYPE=major  # 1.0.0 → 2.0.0
```

## Quality Checks

```bash
make lint       # Check for issues
make lint-fix   # Auto-fix issues
make format     # Format code
make check      # Run all pre-commit hooks
make validate   # Validate JSON files
```

## Script Pattern

All scripts MUST follow:

```python
#!/usr/bin/env python3
# /// script
# dependencies = ["httpx>=0.27.0", "click>=8.1.7"]
# ///

import click

@click.command()
@click.option("--json", "output_json", is_flag=True, help="Output JSON")
def main(output_json: bool) -> None:
    """Command description."""
    pass

if __name__ == "__main__":
    main()
```

**Requirements:**
- UV inline dependencies (NO requirements.txt)
- Click CLI with `--help`
- Dual output: human-readable default + `--json` flag
- Type hints throughout
- Self-contained (no shared imports between scripts)
