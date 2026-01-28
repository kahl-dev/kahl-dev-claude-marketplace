# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **homeassistant**: `delete-entity.py` - Remove entities from registry
- **homeassistant**: `get-logbook.py` - Query logbook entries with filtering
- **homeassistant**: `list-traces.py`, `get-trace.py` - Automation trace debugging
- **homeassistant**: SKILL.md debugging section with trace/logbook workflows
- Makefile with LIA conventions (ASCII art, ##N help system, color output)
- Version bump script (`scripts/bump-version.sh`)
- Enhanced ruff config: `C4` rule, per-file ignores for UV scripts (`E402`, `E501`)
- `docs/contributing.md` guide
- CLAUDE.md: Path references section (`${CLAUDE_PLUGIN_ROOT}` convention)
- CLAUDE.md: Enhanced `get_required_env()` pattern with help_text
- CLAUDE.md: Versioning matrix table
- CLAUDE.md: Contributing workflow + skip hooks tip
- Plugin structure: Add `.claude-plugin/plugin.json` to homeassistant plugin

### Fixed

- `automation-health.py`: Exit 0 on successful run (finding issues is expected behavior, not failure)

## homeassistant [2.0.0] - 2026-01-26

### Added

- **25 new scripts** (26 → 51 total), organized by category:
  - **Entity** (3 new): `search-entities.py`, `get-history.py`, `call-service.py`
  - **Automation** (4 new): `toggle-automation.py`, `list-scenes.py`, `activate-scene.py`, `list-scripts.py`, `run-script.py`
  - **Registry** (11 new): `list-labels.py`, `manage-labels.py`, `list-devices.py`, `update-device.py`, `list-areas.py`, `manage-areas.py`, `list-floors.py`, `manage-floors.py`, `list-categories.py`, `manage-categories.py`, `update-entity.py`
  - **Helpers** (4 new): `manage-helpers.py`, `manage-persons.py`, `manage-zones.py`, `manage-tags.py`
  - **Dashboard** (2 new): `save-dashboard.py`, `delete-dashboard.py`
  - **Backups** (2 new): `list-backups.py`, `manage-backups.py`
  - **Templates** (2 new): `render-template.py`, `fire-event.py`
  - **Integrations** (4 new): `update-core-config.py`, `list-integrations.py`, `manage-integrations.py`, `manage-users.py`
- SKILL.md: Enhanced YAML description with capability taxonomy (10 categories)
- SKILL.md: Safety & Permissions section (read-only vs write vs destructive)
- SKILL.md: API compatibility notes (REST vs WebSocket vs HassOS-only)
- SKILL.md: Scripts capability table with categorized counts

### Changed

- All destructive operations now require `--confirm` flag
- Bulk operations (update-device.py) use continue-all pattern with `--fail-fast` opt-in

### Technical

- WebSocket API: registry, helpers, users, templates (undocumented, verified HA 2026.1.2)
- REST API: dashboards, backups (HassOS/Supervised only for backups)
- Exception handling: specific exceptions (`json.JSONDecodeError`, `KeyError`) over bare `except`

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
