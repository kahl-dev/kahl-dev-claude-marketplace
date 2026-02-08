---
name: new-script
description: Scaffold a new Beyond MCP Python script with UV deps, Click CLI, --json flag, and get_required_env()
user-invocable: true
---

# New Script Scaffolder

Create a new Python script following the Beyond MCP pattern.

## Arguments

- `plugin`: Plugin name (e.g., `homeassistant`)
- `skill`: Skill name (e.g., `homeassistant`)
- `name`: Script name in kebab-case (e.g., `list-widgets`)
- `description`: One-line description of what the script does
- `deps`: Additional Python dependencies beyond `httpx` and `click` (optional)
- `env-vars`: Required environment variables (optional, defaults to plugin's standard vars)

## Workflow

1. Ask for missing arguments interactively
2. Create script at `plugins/<plugin>/skills/<skill>/scripts/<name>.py`
3. Pre-fill with:
   - UV inline dependency block
   - `get_required_env()` helper
   - Click command with `--json` flag
   - Type hints throughout
   - Docstring from description
4. Update SKILL.md script reference table if it has one
5. Report what was created

## Template

```python
#!/usr/bin/env python3
# /// script
# dependencies = ["httpx>=0.27.0", "click>=8.1.7"]
# ///

import json as json_module
import os
import sys

import click
import httpx


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


@click.command()
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def main(output_json: bool) -> None:
    """DESCRIPTION."""
    base_url = get_required_env("HOMEASSISTANT_URL", "Your HA instance URL (e.g., http://192.168.1.x:8123)")
    token = get_required_env("HOMEASSISTANT_TOKEN", "Get from: HA → Profile → Security → Long-Lived Access Tokens")

    headers = {"Authorization": f"Bearer {token}"}

    with httpx.Client(base_url=base_url, headers=headers, timeout=30) as client:
        response = client.get("/api/states")
        response.raise_for_status()
        data = response.json()

    if output_json:
        click.echo(json_module.dumps(data, indent=2))
    else:
        click.echo(f"Found {len(data)} items")


if __name__ == "__main__":
    main()
```

## Customization Points

- Replace `/api/states` with the actual endpoint
- Adjust `get_required_env()` calls for the plugin's env vars
- Add Click options for filtering/parameters
- Implement human-readable output formatting
