# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Makefile with LIA conventions (ASCII art, ##N help system, color output)
- Version bump script (`scripts/bump-version.sh`)
- Enhanced ruff config: `C4` rule, per-file ignores for UV scripts (`E402`, `E501`)
- `docs/contributing.md` guide
- CLAUDE.md: Path references section (`${CLAUDE_PLUGIN_ROOT}` convention)
- CLAUDE.md: Enhanced `get_required_env()` pattern with help_text
- CLAUDE.md: Versioning matrix table
- CLAUDE.md: Contributing workflow + skip hooks tip
- Plugin structure: Add `.claude-plugin/plugin.json` to homeassistant plugin

## homeassistant [1.1.0] - 2026-01-21

### Added

- **Diagnostic scripts** (4 new scripts, 22 → 26 total):
  - `get-system-log.py`: Query HA system logs via WebSocket API
  - `list-repairs.py`: Query Spook repair issues via WebSocket API
  - `check-config.py`: Validate HA configuration via REST API
  - `automation-health.py`: Analyze automations for issues (disabled, stale, unknown entities)
- SKILL.md: New "Diagnostic Operations" section with script reference table
- SKILL.md: Updated triggers to include diagnostic keywords

### Changed

- WebSocket scripts use `urllib.parse` for robust URL handling (supports proxied HA instances)
- WebSocket cleanup improved (handles connection failures gracefully)

### Technical

- Uses `websocket-client` (sync) library - matches existing httpx pattern
- WebSocket endpoints used: `system_log/list`, `repairs/list_issues`, `automation/config`
- Note: These are undocumented HA APIs, verified on HA 2026.1.2

## homeassistant [1.0.3] - 2026-01-21

### Fixed

- SKILL.md: Use correct model identifier `haiku` instead of `claude-haiku-4-5`
- Docs: Fix marketplace install command format (use `owner/repo` not full URL)

## homeassistant [1.0.2] - 2026-01-19

### Changed

- All 20 API scripts now use `get_required_env()` with help_text for better error messages
- `init-config.py` now supports `--json` flag for dual output

### Fixed

- Environment variable errors now show WHERE to get values (e.g., "Get from: HA → Profile → Security")

## homeassistant [1.0.1] - 2025-01-19

### Fixed

- Rewrite `create-automation.py` to match script pattern:
  - Add `--json` flag for dual output support
  - Add `HomeAssistantClient` class with context manager
  - Add proper type hints throughout
  - Remove default `HOMEASSISTANT_URL` (fail-fast pattern)

## [1.0.0] - 2025-01-18

### Added

- Initial release of kahl-dev-claude-marketplace
- **homeassistant** plugin with 22 Python scripts:
  - Entity operations: `list-entities`, `get-state`, `toggle`, `call-service`
  - Automation: `list-automations`, `create-automation`, `trigger-automation`
  - Config deployment: `init-config`, `validate-config`, `deploy-config`, `check-reload`
  - Backup: `trigger-backup`
  - And more...
- Beyond MCP pattern documentation
- SSH setup guide for Home Assistant OS
- Fail-fast environment variable validation
- Protected file handling (`.storage/`, `secrets.yaml`, `*.db`)

### Security

- All scripts use `get_required_env()` for mandatory secrets
- No hardcoded personal values
- rsync excludes protect critical HA files

[Unreleased]: https://github.com/kahl-dev/kahl-dev-claude-marketplace/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/kahl-dev/kahl-dev-claude-marketplace/releases/tag/v1.0.0
