# Architecture & API Reference

## Beyond MCP Pattern

Self-contained UV scripts with inline dependencies (httpx, click, pyyaml). Each script is ~150-300 lines with bearer token authentication and no external state.

## Dual Output Pattern

Every script supports human-readable and JSON output:

```bash
# Human-readable (default)
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/list-entities.py --domain light

# JSON for automation
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/list-entities.py --domain light --json
```

## API Compatibility

| API Type | Scripts | Notes |
|----------|---------|-------|
| REST API | Most scripts | Works on all HA installations |
| WebSocket API | system-log, repairs, registry, helpers, users, templates | Undocumented, verified HA 2026.1.2 |
| Backup REST API | list-backups, manage-backups, trigger-backup | HassOS/Supervised only |
| Dashboard API | save/delete-dashboard | Storage-mode dashboards only |

**Note:** `get-system-log.py`, `list-repairs.py`, registry, and helper scripts use WebSocket API (undocumented, verified on HA 2026.1.2).

## Script Inventory (55 total)

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

## Context Savings

- **Before (MCP):** ~10,000 tokens (10% of context)
- **After (Skill):** ~800 tokens (0.8% of context)
- **Savings: 90%+**
