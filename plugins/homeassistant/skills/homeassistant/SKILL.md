---
name: homeassistant
description: |
  [Claude Code ONLY] Home Assistant control via 55 scripts in ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/.

  **Capabilities (by category):**
  - ENTITY: list, get-state, search, toggle, call-service, history (6 scripts)
  - AUTOMATION: list, toggle, trigger, create (4 scripts)
  - SCENE/SCRIPT: list-scenes, activate-scene, list-scripts, run-script (4 scripts)
  - DASHBOARD: list, get, save, delete (4 scripts)
  - REGISTRY: labels, devices, areas, floors, categories, entities (11 scripts)
  - HELPERS: input_boolean, input_number, timers, counters, persons, zones, tags (4 scripts)
  - CONFIG: init, validate, deploy, check-reload, trigger-backup, list/manage-backups (7 scripts)
  - DIAGNOSTICS: system-log, repairs, check-config, automation-health (4 scripts)
  - DEBUGGING: get-trace, list-traces, get-logbook, delete-entity (4 scripts)
  - TEMPLATES: render-template, fire-event (2 scripts)
  - INTEGRATIONS: list, reload/disable/enable/remove, manage-users, update-core-config (5 scripts)

  **Auto-triggers on:** homeassistant, hass, light, switch, sensor, automation, scene, toggle, turn on/off, dashboard, deploy config, validate config, backup, system log, repairs, health check, diagnostics, template, event, integration, user, label, area, floor, device, helper, zone, category, trace, logbook, debug, orphaned entity.

  **Usage:** Read SKILL.md for script selection → Use --help for syntax (don't read script sources).

  **Destructive operations require --confirm:** delete-dashboard, manage-backups delete/restore, manage-labels delete, manage-areas delete, manage-floors delete, manage-categories delete, manage-integrations remove, manage-users delete, manage-helpers delete, manage-persons delete, manage-zones delete, manage-tags delete, delete-entity.

  **Env vars:** HOMEASSISTANT_URL, HOMEASSISTANT_TOKEN (required); HA_SSH_HOST (for deploy only).
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
| `save-dashboard.py` | Save dashboard config | `lovelace --file dashboard.json` |
| `delete-dashboard.py` | Delete dashboard (--confirm) | `my-dashboard --confirm` |

### System & Config Operations

| Script | Use When | Example |
|--------|----------|---------|
| `get-config.py` | HA version, state | (no args) |
| `init-config.py` | **Bootstrap** local config repo | `--path ~/ha-config` |
| `validate-config.py` | Check YAML, push to staging | `--skip-push` for local only |
| `deploy-config.py` | **Deploy** config to HA | `--dry-run` to preview |
| `trigger-backup.py` | Create HA backup | `--no-wait` |
| `list-backups.py` | List all backups | (no args) |
| `manage-backups.py` | Restore/delete backups | `restore --backup-id abc --confirm` |
| `check-reload.py` | Verify HA health | `--wait 10` |

### Registry Operations

| Script | Use When | Example |
|--------|----------|---------|
| `list-labels.py` | View all labels | `--search "thread"` |
| `manage-labels.py` | Create/update/delete labels | `create --name "Thread" --color red` |
| `list-devices.py` | View all devices | `--label thread --area living_room` |
| `update-device.py` | Update device labels/area | `--device-id abc --labels thread,heizung` |
| `list-areas.py` | View all areas | `--floor ground_floor` |
| `manage-areas.py` | Create/update/delete areas | `create --name "Living Room" --floor ground` |
| `list-floors.py` | View all floors | `--search "ground"` |
| `manage-floors.py` | Create/update/delete floors | `create --name "Ground" --level 0` |
| `list-categories.py` | View categories by scope | `--scope automation` |
| `manage-categories.py` | Create/update/delete categories | `create --scope automation --name "Climate"` |
| `update-entity.py` | Update entity metadata | `--entity-id light.x --area living_room` |

**Bulk operations:**
```bash
# Update multiple devices with same labels
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/update-device.py --device-ids abc,def,ghi --labels thread,batterie

# Update from JSON file
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/update-device.py --from-json device-updates.json
```

**CRUD operations (manage-* scripts):**
```bash
# Create
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/manage-labels.py create --name "Thread" --color blue --icon mdi:network

# Update
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/manage-labels.py update --label-id thread --color red

# Delete (requires --confirm)
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/manage-labels.py delete --label-id thread --confirm
```

### Helper & Entity Operations

| Script | Use When | Example |
|--------|----------|---------|
| `manage-helpers.py` | CRUD for all helper types | `list --type input_boolean` |
| `manage-persons.py` | CRUD for persons | `list`, `create --name "John"` |
| `manage-zones.py` | CRUD for zones | `create --name "Office" --latitude 52.5 --longitude 13.4` |
| `manage-tags.py` | CRUD for NFC/QR tags | `list`, `create --name "Front Door"` |

**Helper types:** input_boolean, input_number, input_text, input_select, input_datetime, input_button, counter, timer, schedule, todo, date, time

**Helper examples:**
```bash
# List input_boolean helpers
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/manage-helpers.py list --type input_boolean

# Create input_number
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/manage-helpers.py create --type input_number --name "Target Temp" --min 15 --max 30 --unit "°C"

# Delete (requires --confirm)
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/manage-helpers.py delete --type input_number --id target_temp --confirm
```

### Diagnostic Operations

| Script | Use When | Example |
|--------|----------|---------|
| `get-system-log.py` | View HA errors/warnings | `--level error --limit 10` |
| `list-repairs.py` | Check Spook repair issues | `--severity warning` |
| `check-config.py` | Validate HA configuration | (no args) |
| `automation-health.py` | Find automation issues | `--check-entities --stale-days 30` |

**Note:** `get-system-log.py`, `list-repairs.py`, registry, and helper scripts use WebSocket API (undocumented, verified on HA 2026.1.2).

### Debugging Operations

| Script | Use When | Example |
|--------|----------|---------|
| `list-traces.py` | List automation execution traces | `automation.my_automation` or `--domain automation` |
| `get-trace.py` | View specific trace details | `automation.my_automation` or `--run-id abc123` |
| `get-logbook.py` | Query logbook entries | `--hours 24 --entity automation.test` |
| `delete-entity.py` | Delete orphaned entities | `sensor.orphaned --confirm` |

**Debugging workflow:**
```bash
# 1. Find what happened (list recent traces)
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/list-traces.py --domain automation

# 2. View trace details (smart formatted, shows executed path)
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/get-trace.py automation.my_automation

# 3. With verbose output (all variable values)
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/get-trace.py automation.my_automation --verbose

# 4. Query logbook for related events
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/get-logbook.py --entity automation.my_automation --hours 24

# 5. Clean up orphaned entity (dry-run first)
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/delete-entity.py automation.old_test
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/delete-entity.py automation.old_test --confirm
```

**Tip:** HA stores only 5 traces per automation by default. Add `trace: stored_traces: 20` to automation YAML for better debugging history.

### Templates & Events

| Script | Use When | Example |
|--------|----------|---------|
| `render-template.py` | Render Jinja2 templates | `"{{ states('sensor.temp') }}"` |
| `fire-event.py` | Fire custom events | `my_event --data '{"key": "value"}'` |

**Template examples:**
```bash
# Simple state
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/render-template.py "{{ states('sun.sun') }}"

# Count entities
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/render-template.py "{{ states.light | list | count }} lights"

# From file
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/render-template.py --file template.j2
```

### Integration & User Management

| Script | Use When | Example |
|--------|----------|---------|
| `update-core-config.py` | Update HA core settings | `--location-name "Home" --time-zone Europe/Berlin` |
| `list-integrations.py` | List config entries | `--domain zha --state loaded` |
| `manage-integrations.py` | Reload/disable/enable/remove | `reload --entry-id abc123` |
| `manage-users.py` | List/create/delete users | `list --exclude-system` |

**Integration examples:**
```bash
# List all integrations
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/list-integrations.py

# Reload specific integration
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/manage-integrations.py reload --entry-id abc123

# Remove integration (requires --confirm)
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/manage-integrations.py remove --entry-id abc123 --confirm
```

**User examples:**
```bash
# List users (excluding system accounts)
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/manage-users.py list --exclude-system

# Create user (credentials set via HA UI after)
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/manage-users.py create --name "Guest"

# Create admin user
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/manage-users.py create --name "Admin" --admin

# Delete user (requires --confirm)
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/manage-users.py delete --user-id abc123 --confirm
```

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

### ⚠️ Protected Files (NEVER overwritten)

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

| Category | Count | Scripts |
|----------|-------|---------|
| Entity | 6 | list-entities, get-state, search-entities, toggle, call-service, get-history |
| Automation | 4 | list-automations, toggle-automation, trigger-automation, create-automation |
| Scene/Script | 4 | list-scenes, activate-scene, list-scripts, run-script |
| Dashboard | 4 | list-dashboards, get-dashboard, save-dashboard, delete-dashboard |
| Registry | 11 | list/manage-labels, list-devices, update-device, list/manage-areas, list/manage-floors, list/manage-categories, update-entity |
| Helpers | 4 | manage-helpers, manage-persons, manage-zones, manage-tags |
| Config | 7 | get-config, init-config, validate-config, deploy-config, trigger-backup, list-backups, manage-backups |
| Diagnostics | 4 | get-system-log, list-repairs, check-config, automation-health |
| Debugging | 4 | list-traces, get-trace, get-logbook, delete-entity |
| Templates | 2 | render-template, fire-event |
| Integrations | 5 | update-core-config, list-integrations, manage-integrations, manage-users, check-reload |
| **Total** | **55** | |

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

## Safety & Permissions

### Read-Only Operations (Safe)
All `list-*.py`, `get-*.py`, `search-*.py`, `check-*.py` scripts are read-only.

### Write Operations (Require Care)
| Operation | Confirmation | Risk Level |
|-----------|--------------|------------|
| `toggle.py`, `call-service.py` | None | Low (reversible) |
| `activate-scene.py`, `run-script.py` | None | Low (executes HA scripts) |
| `trigger-automation.py` | None | Medium (runs automation) |
| `create-automation.py` | None | Medium (creates config) |
| `save-dashboard.py` | None | Medium (overwrites dashboard) |
| `fire-event.py` | None | Medium (triggers automations) |
| `update-*.py` | None | Medium (modifies metadata) |
| `manage-*.py create/update` | None | Medium (creates/modifies) |
| `deploy-config.py` | --dry-run available | High (deploys to HA) |
| `update-core-config.py` | None | High (changes HA settings) |

### Destructive Operations (Require --confirm)
| Script | What It Does |
|--------|--------------|
| `delete-dashboard.py` | Permanently deletes dashboard |
| `manage-backups.py delete` | Permanently deletes backup |
| `manage-backups.py restore` | Restarts HA, overwrites config |
| `manage-labels.py delete` | Removes label from all entities |
| `manage-areas.py delete` | Removes area assignments |
| `manage-floors.py delete` | Removes floor assignments |
| `manage-categories.py delete` | Removes category assignments |
| `manage-integrations.py remove` | Removes integration config |
| `manage-users.py delete` | Deletes user account |
| `manage-helpers.py delete` | Deletes helper entity |
| `manage-persons.py delete` | Deletes person entity |
| `manage-zones.py delete` | Deletes zone |
| `manage-tags.py delete` | Deletes NFC/QR tag |

### API Compatibility
| API Type | Scripts | Notes |
|----------|---------|-------|
| REST API | Most scripts | Works on all HA installations |
| WebSocket API | system-log, repairs, registry, helpers, users, templates | Undocumented, verified HA 2026.1.2 |
| Backup REST API | list-backups, manage-backups, trigger-backup | HassOS/Supervised only |
| Dashboard API | save/delete-dashboard | Storage-mode dashboards only |

## Context Savings

- **Before (MCP):** ~10,000 tokens (10% of context)
- **After (Skill):** ~800 tokens (0.8% of context)
- **Savings: 90%+**
