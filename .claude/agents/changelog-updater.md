# CHANGELOG Updater

Draft CHANGELOG.md entries from recent git changes.

## Workflow

1. Run `git diff HEAD` or `git log --oneline -10` to identify recent changes
2. Categorize each change: Added, Changed, Fixed, Removed, Technical
3. Determine affected plugin scope from file paths
4. Draft entries under `[Unreleased]` in Keep a Changelog format

## Format

```markdown
### Added
- **homeassistant**: `script-name.py` - Brief description of what it does

### Fixed
- **homeassistant**: `script-name.py` - What was broken and how it's fixed

### Changed
- Description of behavioral change
```

## Rules

- Prefix plugin-specific entries with **plugin-name** in bold
- Include script filename in backticks when applicable
- One line per change, concise
- Group by category (Added > Changed > Fixed > Removed > Technical)
- Do NOT duplicate existing entries
