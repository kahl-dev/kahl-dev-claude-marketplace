# Home Assistant Script Examples

Detailed usage examples for complex operations. For script selection, see SKILL.md tables.

## Bulk Registry Operations

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

## Helper Operations

**Helper types:** input_boolean, input_number, input_text, input_select, input_datetime, input_button, counter, timer, schedule, todo, date, time

```bash
# List input_boolean helpers
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/manage-helpers.py list --type input_boolean

# Create input_number
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/manage-helpers.py create --type input_number --name "Target Temp" --min 15 --max 30 --unit "°C"

# Delete (requires --confirm)
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/manage-helpers.py delete --type input_number --id target_temp --confirm
```

## Debugging Workflow

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

## Template & Event Examples

```bash
# Simple state
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/render-template.py "{{ states('sun.sun') }}"

# Count entities
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/render-template.py "{{ states.light | list | count }} lights"

# From file
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/render-template.py --file template.j2

# Fire custom event
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/fire-event.py my_event --data '{"key": "value"}'
```

## Integration & User Management

```bash
# List all integrations
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/list-integrations.py

# Reload specific integration
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/manage-integrations.py reload --entry-id abc123

# Remove integration (requires --confirm)
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/manage-integrations.py remove --entry-id abc123 --confirm
```

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

## Config Deployment

**Additional env vars for deployment (optional, have defaults):**
```bash
export HA_CONFIG_PATH="/homeassistant"                    # Default: /homeassistant
export HA_STAGING_PATH="/homeassistant/config_staging"    # Default
```

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

### Protected Files (NEVER overwritten by deploy)

| Path | Reason |
|------|--------|
| `.storage/` | Device registries, Zigbee/Z-Wave networks, auth tokens |
| `secrets.yaml` | Production secrets (never deploy from git!) |
| `backups/` | Backup files |
| `*.db` | SQLite databases |
| `home-assistant.log*` | Log files |
| `tts/` | Text-to-speech cache |
| `deps/` | Python dependencies |
