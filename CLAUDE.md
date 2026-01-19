# kahl-dev-claude-marketplace

Claude Code plugin marketplace using the **Beyond MCP** pattern - self-contained Python scripts with UV inline dependencies. Achieves 90%+ context savings (~800 tokens vs ~10,000).

## Structure

```
.claude-plugin/marketplace.json    # Marketplace definition (version here)
plugins/
└── homeassistant/
    ├── skills/homeassistant/
    │   ├── SKILL.md               # Progressive disclosure guide
    │   └── scripts/               # 22 Python scripts
    └── docs/                      # User documentation
```

## Development Setup

```bash
# Install dev dependencies (pre-commit, ruff)
uv sync

# Pre-commit hooks auto-install on first commit
# Manual install: uv run pre-commit install
```

## Commands

### Linting

```bash
uv run ruff check .        # Lint all files
uv run ruff check --fix .  # Auto-fix issues
uv run ruff format .       # Format all files
uv run pre-commit run --all-files  # Run all hooks
```

### Testing Scripts

```bash
# All scripts use UV inline dependencies - no venv needed
uv run plugins/homeassistant/skills/homeassistant/scripts/<script>.py --help

# Example
uv run plugins/homeassistant/skills/homeassistant/scripts/list-entities.py --domain light
```

### Validation

```bash
# Verify all scripts compile
find plugins -name "*.py" -exec python -m py_compile {} \;

# Check for hardcoded values (should return empty)
grep -r "casa-kahl\|home-command-center" plugins/
```

## Script Pattern

All scripts MUST follow this structure:

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

**Required:**
- UV inline dependencies (NO requirements.txt)
- Click CLI with `--help`
- Dual output: human-readable default + `--json` flag
- Type hints throughout
- Self-contained (intentional duplication for isolation)
- `get_required_env()` for mandatory env vars (fail fast)

## SKILL.md Pattern

Keep SKILL.md concise (~800 tokens):
- YAML frontmatter: name, description, triggers
- Quick reference tables (script → use case → example)
- Environment variable requirements
- Links to scripts, NOT duplicated docs

## Versioning

Version lives in `.claude-plugin/marketplace.json`.

**When to bump:**
- `patch` (1.0.x): Bug fixes, doc updates, typos
- `minor` (1.x.0): New scripts, new features
- `major` (x.0.0): Breaking changes, removed scripts

**Release workflow:**
1. Update `version` in `marketplace.json`
2. Update CHANGELOG.md
3. Commit: `chore(release): bump version to x.x.x`
4. Push to main

## Commit Conventions

**Enforced by pre-commit hook** - commits rejected if format invalid.

Format: `<type>(<scope>): <description>`

```
feat(homeassistant): add new script for X
fix(homeassistant): correct validation logic
docs: update installation instructions
chore(release): bump version to 1.1.0
refactor: simplify error handling
```

**Types:** `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `style`, `perf`
**Scopes:** `homeassistant`, `marketplace`, `docs`, or omit for root changes

**On commit:** ruff auto-fixes + formats staged Python files

## Adding a New Plugin

1. Create structure:
   ```
   plugins/<name>/
   ├── skills/<skill>/
   │   ├── SKILL.md
   │   └── scripts/
   ├── docs/
   └── README.md
   ```

2. Add to `marketplace.json`:
   ```json
   {
     "name": "plugin-name",
     "description": "...",
     "source": "./plugins/plugin-name",
     "keywords": ["..."],
     "license": "MIT"
   }
   ```

3. Update root README.md plugin table

## Security

- NEVER log or commit tokens
- Protected files in deploy scripts: `.storage/`, `secrets.yaml`, `*.db`
- Use `get_required_env()` for secrets - fail fast, clear error messages
- All secrets via environment variables

## Critical Warnings

- NEVER add personal data (hostnames, paths, IPs)
- ALWAYS use `os.path.expanduser()` for paths with `~`
- ALWAYS provide `--help` on all scripts
- Pre-commit hooks run automatically - no need to lint manually before commit
