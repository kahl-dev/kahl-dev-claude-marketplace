---
name: release
description: Orchestrate plugin release - finalize CHANGELOG, bump version, update docs
user-invocable: true
disable-model-invocation: true
---

# Plugin Release

Orchestrate the full release workflow for a plugin.

## Arguments

- `plugin`: Plugin name (e.g., `homeassistant`)
- `type`: Version bump type (`patch`, `minor`, `major`)

## Workflow

1. **Pre-flight checks**:
   - Verify working tree is clean (`git status`)
   - Verify `[Unreleased]` section in CHANGELOG.md has entries
   - Read current version from `plugins/<plugin>/.claude-plugin/plugin.json`

2. **CHANGELOG finalization**:
   - Calculate new version based on bump type
   - Move `[Unreleased]` entries to `[<new-version>] - <today's date>` section
   - Add fresh empty `[Unreleased]` section
   - Update comparison links at bottom

3. **Version bump**:
   - Run `make bump PLUGIN=<plugin> TYPE=<type>`

4. **Verification**:
   - Run `make validate` to check JSON integrity
   - Run `make test-scripts` to verify Python syntax
   - Show summary of changes

5. **Commit** (with user confirmation):
   - Stage CHANGELOG.md + plugin.json
   - Commit as `chore(<plugin>): release <new-version>`

## Example

```
/release homeassistant minor
```

Produces:
- `plugins/homeassistant/.claude-plugin/plugin.json`: version `2.2.0` → `2.3.0`
- `CHANGELOG.md`: `[Unreleased]` entries moved to `[2.3.0] - 2026-02-08`
- Commit: `chore(homeassistant): release 2.3.0`
