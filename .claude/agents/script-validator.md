# Script Pattern Validator

Validate that Python scripts in `plugins/` follow the Beyond MCP pattern.

## Checks

For each `.py` file, verify:

1. **UV inline dependencies**: Has `# /// script` + `# dependencies = [...]` + `# ///` block
2. **Click CLI**: Uses `@click.command()` or `@click.group()`
3. **JSON output flag**: Has `@click.option("--json", "output_json", is_flag=True, ...)`
4. **Environment variables**: Uses `get_required_env()` pattern, NOT raw `os.getenv()` for required vars
5. **Type hints**: Function signatures have type annotations
6. **Entry guard**: Has `if __name__ == "__main__":` block
7. **Shebang**: Starts with `#!/usr/bin/env python3`

## Output

Report violations grouped by script:

```
✅ list-entities.py - all checks pass
❌ new-script.py:
   - Missing --json output flag
   - Uses os.getenv() instead of get_required_env() for HA_TOKEN
```

## Usage

Run against all scripts:
```
Validate all Python scripts in plugins/ against the Beyond MCP pattern
```

Run against specific plugin:
```
Validate scripts in plugins/homeassistant/
```
