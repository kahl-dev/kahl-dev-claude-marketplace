# Config Deployment Workflow

This guide explains the complete workflow for editing and deploying Home Assistant configuration.

## Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    Your Machine                               │
│  ┌─────────────────┐    ┌─────────────────┐                  │
│  │  Local Git Repo │───>│ validate-config │                  │
│  │  ~/ha-config/   │    │    (YAML check) │                  │
│  └─────────────────┘    └────────┬────────┘                  │
└────────────────────────────────────────────────────────────────┘
                                    │ rsync
                                    ▼
┌──────────────────────────────────────────────────────────────┐
│                  Home Assistant                               │
│  ┌─────────────────┐    ┌─────────────────┐                  │
│  │ /config_staging │───>│ deploy-config   │                  │
│  │  (validation)   │    │  (production)   │                  │
│  └─────────────────┘    └────────┬────────┘                  │
│                                  │                            │
│                                  ▼                            │
│                         ┌─────────────────┐                  │
│                         │    /config      │                  │
│                         │  (production)   │                  │
│                         └─────────────────┘                  │
└──────────────────────────────────────────────────────────────┘
```

## Step-by-Step

### 1. Bootstrap (One-Time)

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/init-config.py
```

This:
- Creates `~/ha-config/` directory
- Pulls current config from HA
- Initializes git repository
- Creates `.gitignore`
- Makes initial commit

### 2. Edit Configuration

Edit YAML files in your local directory:

```bash
# Manual editing
vim ~/ha-config/configuration.yaml

# Or let Claude edit
# "Add a new automation for the bedroom lights"
```

### 3. Validate

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/validate-config.py
```

This:
- Checks YAML syntax locally
- Pushes to staging directory on HA
- Copies secrets.yaml for completeness

**If validation fails**, fix the errors and re-validate.

### 4. Deploy

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/deploy-config.py
```

This:
- Re-validates (safety check)
- Creates automatic backup
- Deploys to production (with protected file exclusions)
- Reloads HA services
- Verifies health

### 5. Verify

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/check-reload.py
```

Check that HA is healthy and no errors appeared.

### 6. Commit

```bash
cd ~/ha-config
git add -A
git commit -m "Add bedroom automation"
```

## Dry-Run Mode

Preview what would be deployed without making changes:

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/deploy-config.py --dry-run
```

## Skip Backup

For quick iterations (not recommended for production):

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/deploy-config.py --no-backup
```

## Protected Files

These files are **NEVER** overwritten during deployment:

| File/Directory | Reason |
|----------------|--------|
| `.storage/` | Device registries, entity registry, auth, Zigbee/Z-Wave networks |
| `secrets.yaml` | Production secrets (never from git!) |
| `*.db` | SQLite databases |
| `backups/` | Backup files |
| `home-assistant.log*` | Log files |
| `tts/` | TTS cache |
| `deps/` | Python dependencies |

## Syncing Changes FROM HA

If you made changes directly in HA (via UI):

```bash
# Pull changes to staging
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/validate-config.py

# Then manually rsync staging to local
rsync -av $HA_SSH_HOST:$HA_STAGING_PATH/ ~/ha-config/

# Review and commit
cd ~/ha-config
git diff
git add -A
git commit -m "Sync changes from HA UI"
```

## Troubleshooting

### "YAML validation failed"

Check the error output - it will show the file and line number.

### "SSH connection failed"

Verify SSH works:
```bash
ssh $HA_SSH_HOST "echo ok"
```

See [SSH Setup](ssh-setup.md) for configuration help.

### "Backup failed"

Backups may fail if:
- Backup API not available (older HA versions)
- Insufficient disk space

Use `--no-backup` to skip (not recommended).

### "Reload failed"

Check HA logs:
```bash
ssh $HA_SSH_HOST "tail -50 /homeassistant/home-assistant.log"
```
