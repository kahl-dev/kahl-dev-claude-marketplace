# kahl-dev-claude-marketplace

Claude Code plugin marketplace using the **Beyond MCP** pattern - self-contained Python scripts with UV inline dependencies. Achieves 90%+ context savings (~800 tokens vs ~10,000).

## Structure

```
.claude-plugin/marketplace.json    # Marketplace definition
plugins/
└── <plugin-name>/
    ├── .claude-plugin/plugin.json # Plugin manifest (version here)
    ├── skills/<skill>/
    │   ├── SKILL.md               # Progressive disclosure guide
    │   └── scripts/               # Python scripts
    └── docs/                      # User documentation
scripts/
└── bump-version.sh                # Version automation
docs/
└── contributing.md                # Contribution guide
```

## Path References (CRITICAL)

**ALWAYS use `${CLAUDE_PLUGIN_ROOT}`, NEVER absolute paths!**

```bash
# ✅ CORRECT
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/list-entities.py

# ❌ WRONG (breaks for other users)
uv run ~/.claude/skills/homeassistant/scripts/list-entities.py
```

**Why:** Plugins install to `~/.claude/plugins/<name>@<marketplace>/`.

## Development Setup

```bash
make setup  # Install deps + git hooks (one-time)
```

## Commands

```bash
# Development
make lint       # Check for issues
make lint-fix   # Auto-fix issues
make format     # Format code
make bump PLUGIN=homeassistant TYPE=patch  # Version bump

# Quality
make check        # Run all pre-commit hooks
make validate     # Validate JSON files
make test-scripts # Verify Python syntax
```

### Testing Scripts

```bash
uv run plugins/<plugin>/skills/<skill>/scripts/<script>.py --help
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

**Environment variable pattern:**

```python
def get_required_env(name: str, help_text: str = "") -> str:
    """Get required environment variable or fail fast."""
    value = os.getenv(name)
    if not value:
        click.echo(f"❌ Error: {name} not set.", err=True)
        if help_text:
            click.echo(f"   {help_text}", err=True)
        click.echo(f'   Set: export {name}="<value>"', err=True)
        sys.exit(1)
    return value

# Usage with help_text
HA_TOKEN = get_required_env(
    "HA_TOKEN",
    "Get from: HA → Profile → Security → Long-Lived Access Tokens"
)
```

## SKILL.md Pattern

Keep SKILL.md concise (~800 tokens):
- YAML frontmatter: name, description, triggers
- Quick reference tables (script → use case → example)
- Environment variable requirements
- Links to scripts, NOT duplicated docs

## Versioning

Plugin versions in `plugins/<name>/.claude-plugin/plugin.json`.

```bash
make bump PLUGIN=homeassistant TYPE=patch  # 1.0.0 → 1.0.1
make bump PLUGIN=homeassistant TYPE=minor  # 1.0.0 → 1.1.0
make bump PLUGIN=homeassistant TYPE=major  # 1.0.0 → 2.0.0
```

| Change Type | CHANGELOG | plugin.json | marketplace.json |
|-------------|-----------|-------------|------------------|
| Bug fix | ✅ [Unreleased] | ✅ PATCH | ❌ |
| New feature | ✅ [Unreleased] | ✅ MINOR | ❌ |
| Breaking change | ✅ [Unreleased] | ✅ MAJOR | ❌ |
| New plugin | ✅ [Unreleased] | ✅ 1.0.0 | ✅ Add entry |

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

**Skip hooks (emergency only):**
```bash
git commit --no-verify -m "message"
```

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

## Contributing Workflow

1. `make setup` (first time)
2. Make changes with conventional commits
3. Update CHANGELOG.md under `[Unreleased]`
4. `make bump PLUGIN=<name> TYPE=<type>`
5. Push to main
