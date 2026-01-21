---
name: homeassistant
description: |
  [Claude Code ONLY] Home Assistant control via scripts in ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/.
  Auto-triggers on: homeassistant, hass, light, switch, sensor, automation, scene, toggle, turn on/off, dashboard, deploy config, validate config, backup, system log, repairs, health check, diagnostics.
  Read SKILL.md guide to know which script for your task. Use --help for syntax (don't read script sources).
  Scripts provide entity control, automations, scenes, scripts, dashboards, history, AND config file deployment.
  Requires env vars: HOMEASSISTANT_URL, HOMEASSISTANT_TOKEN, HA_SSH_HOST (for deploy). Always use absolute paths.
model: haiku
---

# Home Assistant Scripts Skill

Progressive disclosure pattern for Home Assistant operations achieving 90%+ context savings.

## Quick Start

```bash
# Bootstrap local config repo (one-time)
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/init-config.py

# Common operations
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/list-entities.py --domain light
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/toggle.py light.bedroom on
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/deploy-config.py --dry-run
```

## How This Works

1. Check this guide to know which script to use
2. Run `<script>.py --help` to see exact syntax
3. Execute with: `uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/<script>.py`

## Environment Variables

```bash
# Required for all scripts
export HOMEASSISTANT_URL="http://homeassistant.local:8123"
export HOMEASSISTANT_TOKEN="<long-lived-access-token>"

# Required for config deployment (NO DEFAULT - must be set!)
export HA_SSH_HOST="<your-ssh-alias>"

# Optional (have sensible defaults)
export HA_LOCAL_CONFIG="~/ha-config"              # Default: ~/ha-config
export HA_CONFIG_PATH="/homeassistant"            # Default: /homeassistant
export HA_STAGING_PATH="/homeassistant/config_staging"  # Default
```

**Get token:** HA Profile → Security → Long-Lived Access Tokens → Create

**SSH setup:** Ensure `ssh $HA_SSH_HOST` works without password

## When to Use Each Script

### Entity Operations

| Script | Use When | Example |
|--------|----------|---------|
| `list-entities.py` | Overview of entities by domain | `--domain light` |
| `get-state.py` | Full details for one entity | `light.living_room` |
| `search-entities.py` | Find entities by pattern | `"bedroom" --domain light` |
| `toggle.py` | Quick on/off toggle | `light.bedroom on` |
| `call-service.py` | Full control (brightness, colors) | `light turn_on --entity light.bedroom --data '{"brightness_pct": 50}'` |
| `get-history.py` | Past states, sensor trends | `sensor.temperature --hours 24` |

### Automation Operations

| Script | Use When | Example |
|--------|----------|---------|
| `list-automations.py` | View all automations | `--enabled` |
| `toggle-automation.py` | Enable/disable | `automation.morning on` |
| `trigger-automation.py` | Manual trigger | `automation.test --skip-condition` |
| `create-automation.py` | Create via API | `'{"id": "test", ...}'` |

### Scene & Script Operations

| Script | Use When | Example |
|--------|----------|---------|
| `list-scenes.py` | View scenes | (no args) |
| `activate-scene.py` | Activate scene | `scene.movie_night` |
| `list-scripts.py` | View HA scripts | `--running` |
| `run-script.py` | Execute script | `script.notify --data '{"message": "Hi"}'` |

### Dashboard Operations

| Script | Use When | Example |
|--------|----------|---------|
| `list-dashboards.py` | View dashboards | (no args) |
| `get-dashboard.py` | Dashboard config | `lovelace --view 0` |

### System & Config Operations

| Script | Use When | Example |
|--------|----------|---------|
| `get-config.py` | HA version, state | (no args) |
| `init-config.py` | **Bootstrap** local config repo | `--path ~/ha-config` |
| `validate-config.py` | Check YAML, push to staging | `--skip-push` for local only |
| `deploy-config.py` | **Deploy** config to HA | `--dry-run` to preview |
| `trigger-backup.py` | Create HA backup | `--no-wait` |
| `check-reload.py` | Verify HA health | `--wait 10` |

### Diagnostic Operations

| Script | Use When | Example |
|--------|----------|---------|
| `get-system-log.py` | View HA errors/warnings | `--level error --limit 10` |
| `list-repairs.py` | Check Spook repair issues | `--severity warning` |
| `check-config.py` | Validate HA configuration | (no args) |
| `automation-health.py` | Find automation issues | `--check-entities --stale-days 30` |

**Note:** `get-system-log.py` and `list-repairs.py` use WebSocket API (undocumented, verified on HA 2026.1.2).

## Config Deployment Workflow

**Edit → Validate → Deploy → Verify**

```bash
# 1. Bootstrap (one-time)
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/init-config.py

# 2. Edit local YAML files
# (use Claude Edit tool on ~/ha-config/*.yaml)

# 3. Validate (checks YAML, pushes to staging)
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/validate-config.py

# 4. Deploy (backup → deploy → reload)
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/deploy-config.py

# 5. Verify health
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/check-reload.py
```

### Dry-run mode

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/deploy-config.py --dry-run
```

### ⚠️ CRITICAL: Protected Files (NEVER overwritten)

| Path | Reason |
|------|--------|
| `.storage/` | Device registries, Zigbee/Z-Wave networks, auth tokens |
| `secrets.yaml` | Production secrets (never deploy from git!) |
| `backups/` | Backup files |
| `*.db` | SQLite databases |
| `home-assistant.log*` | Log files |
| `tts/` | Text-to-speech cache |
| `deps/` | Python dependencies |

These are excluded from rsync to protect your installation.

## Script Locations

All scripts: `${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/`

- 6 entity operations
- 4 automation operations
- 2 scene operations
- 2 script operations
- 2 dashboard operations
- 1 system operation
- 5 config operations
- 4 diagnostic operations
- **Total: 26 scripts**

## Dual Output Pattern

Every script supports human-readable and JSON output:

```bash
# Human-readable (default)
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/list-entities.py --domain light

# JSON for automation
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/list-entities.py --domain light --json
```

## Architecture

Following **Beyond MCP** pattern:
- UV inline dependencies (httpx, click, pyyaml)
- Self-contained scripts (~150-300 lines each)
- Bearer token authentication
- No external state

## Context Savings

- **Before (MCP):** ~10,000 tokens (10% of context)
- **After (Skill):** ~800 tokens (0.8% of context)
- **Savings: 90%+**
