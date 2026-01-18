# 🏠 Home Assistant Plugin for Claude Code

Control Home Assistant and deploy configurations directly from Claude Code.

## Features

- **Entity Control**: Toggle lights, set temperatures, control any device
- **Automation Management**: Create, trigger, enable/disable automations
- **Config Deployment**: Edit YAML locally → validate → deploy with backup
- **Beyond MCP Pattern**: 90%+ context savings vs traditional MCP servers

## Quick Start

### 1. Set Environment Variables

```bash
# Required
export HOMEASSISTANT_URL="http://homeassistant.local:8123"
export HOMEASSISTANT_TOKEN="<your-long-lived-token>"

# For config deployment (NO DEFAULT!)
export HA_SSH_HOST="<your-ssh-alias>"
```

**Get token:** HA Profile → Security → Long-Lived Access Tokens → Create

### 2. Bootstrap Config Repo (Optional)

If you want to deploy config changes:

```bash
uv run ~/.claude/skills/homeassistant/scripts/init-config.py
```

### 3. Use in Claude Code

Just ask Claude:
- "Turn on the bedroom light"
- "List all automations"
- "Deploy my Home Assistant config"
- "Show sensor history for the last 24 hours"

## Scripts Overview

| Category | Scripts | Description |
|----------|---------|-------------|
| Entity | 6 | list, get, search, toggle, call-service, history |
| Automation | 4 | list, toggle, trigger, create |
| Scene | 2 | list, activate |
| Script | 2 | list, run |
| Dashboard | 2 | list, get |
| Config | 5 | init, validate, deploy, backup, check-reload |
| System | 1 | get-config |
| **Total** | **22** | |

## Config Deployment Workflow

```
Edit (local) → Validate → Backup → Deploy → Reload → Verify
```

**Safety features:**
- YAML validation before deployment
- Automatic backup before changes
- Protected files never overwritten (.storage/, secrets.yaml, *.db)
- Staging directory for safe validation
- Dry-run mode to preview changes

## Documentation

- [Installation Guide](docs/installation.md)
- [SSH Setup](docs/ssh-setup.md)
- [HA Install Types](docs/ha-install-types.md)
- [Deployment Workflow](docs/workflow.md)

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (for running scripts)
- SSH access to Home Assistant (for config deployment)
- Home Assistant 2024.x+ (tested with 2025.x)

## License

MIT - See [LICENSE](../../LICENSE)
