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
