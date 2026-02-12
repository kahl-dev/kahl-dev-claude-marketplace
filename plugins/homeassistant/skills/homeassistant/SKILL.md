---
name: homeassistant
description: |
  [Claude Code ONLY] Home Assistant control via 55 scripts in ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/.

  **Auto-triggers on:** homeassistant, hass, light, switch, sensor, automation, scene, toggle, turn on/off, dashboard, deploy config, validate config, backup, system log, repairs, health check, diagnostics, template, event, integration, user, label, area, floor, device, helper, zone, category, trace, logbook, debug, orphaned entity.

  **Usage:** Read SKILL.md for script selection → Use --help for syntax (don't read script sources).

  **Env vars:** HOMEASSISTANT_URL, HOMEASSISTANT_TOKEN (required); HA_SSH_HOST (for deploy only).
---

# Home Assistant Scripts Skill

55 self-contained UV scripts for full Home Assistant control via REST + WebSocket APIs.

## Quick Start

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/list-entities.py --domain light
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/toggle.py light.bedroom on
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/deploy-config.py --dry-run
```

## How This Works

1. Check tables below to find the right script
2. Run `<script>.py --help` for exact syntax
3. Execute with: `uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/<script>.py`

## Environment Variables

```bash
export HOMEASSISTANT_URL="http://homeassistant.local:8123"  # Required
export HOMEASSISTANT_TOKEN="<long-lived-access-token>"       # Required
export HA_SSH_HOST="<your-ssh-alias>"                        # For deploy only
export HA_LOCAL_CONFIG="~/ha-config"                         # Default: ~/ha-config
```

## Script Selection

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

### Config & Deployment

| Script | Use When | Example |
|--------|----------|---------|
| `get-config.py` | HA version, state | (no args) |
| `init-config.py` | Bootstrap local config repo | `--path ~/ha-config` |
| `validate-config.py` | Check YAML, push to staging | `--skip-push` |
| `deploy-config.py` | Deploy config to HA | `--dry-run` |
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

### Helper & Person Operations

| Script | Use When | Example |
|--------|----------|---------|
| `manage-helpers.py` | CRUD for all helper types | `list --type input_boolean` |
| `manage-persons.py` | CRUD for persons | `list`, `create --name "John"` |
| `manage-zones.py` | CRUD for zones | `create --name "Office" --latitude 52.5 --longitude 13.4` |
| `manage-tags.py` | CRUD for NFC/QR tags | `list`, `create --name "Front Door"` |

### Diagnostics & Debugging

| Script | Use When | Example |
|--------|----------|---------|
| `get-system-log.py` | View HA errors/warnings | `--level error --limit 10` |
| `list-repairs.py` | Check Spook repair issues | `--severity warning` |
| `check-config.py` | Validate HA configuration | (no args) |
| `automation-health.py` | Find automation issues | `--check-entities --stale-days 30` |
| `list-traces.py` | List execution traces | `automation.my_auto` or `--domain automation` |
| `get-trace.py` | View trace details | `automation.my_auto` or `--run-id abc123` |
| `get-logbook.py` | Query logbook entries | `--hours 24 --entity automation.test` |
| `delete-entity.py` | Delete orphaned entities | `sensor.orphaned --confirm` |

### Templates, Events & Integrations

| Script | Use When | Example |
|--------|----------|---------|
| `render-template.py` | Render Jinja2 templates | `"{{ states('sensor.temp') }}"` |
| `fire-event.py` | Fire custom events | `my_event --data '{"key": "value"}'` |
| `update-core-config.py` | Update HA core settings | `--location-name "Home" --time-zone Europe/Berlin` |
| `list-integrations.py` | List config entries | `--domain zha --state loaded` |
| `manage-integrations.py` | Reload/disable/enable/remove | `reload --entry-id abc123` |
| `manage-users.py` | List/create/delete users | `list --exclude-system` |

## Safety

**Read-only (safe):** All `list-*.py`, `get-*.py`, `search-*.py`, `check-*.py` scripts.

**Destructive (require `--confirm`):** `delete-dashboard`, `manage-backups delete/restore`, `manage-labels delete`, `manage-areas delete`, `manage-floors delete`, `manage-categories delete`, `manage-integrations remove`, `manage-users delete`, `manage-helpers delete`, `manage-persons delete`, `manage-zones delete`, `manage-tags delete`, `delete-entity`.

**High risk:** `deploy-config.py` (use `--dry-run` first), `update-core-config.py`.

## Additional Resources

For detailed examples, debugging workflows, and bulk operations:
- **`references/examples.md`** — Verbose examples for all script categories, config deployment workflow, debugging workflow, bulk registry operations
- **`references/architecture.md`** — API compatibility matrix, full 55-script inventory table, Beyond MCP pattern, context savings analysis
