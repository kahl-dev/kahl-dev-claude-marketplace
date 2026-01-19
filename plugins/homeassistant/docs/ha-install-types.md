# Home Assistant Installation Types

This guide helps you configure the plugin for different HA installation types.

## Overview

| Type | Config Path | SSH Port | Notes |
|------|-------------|----------|-------|
| HA OS | `/homeassistant` | 22222 | Recommended, runs on dedicated hardware |
| Container | Varies | 22 | Docker/Podman on existing server |
| Core | `~/.homeassistant` | 22 | Python venv on existing system |
| Supervised | `/homeassistant` | 22222 | HA OS features on custom OS |

## Home Assistant OS

The recommended installation method.

```bash
# Environment variables
export HA_CONFIG_PATH="/homeassistant"
export HA_STAGING_PATH="/homeassistant/config_staging"

# SSH config (~/.ssh/config)
Host ha
  HostName homeassistant.local
  User root
  Port 22222
```

**Note:** Requires SSH & Web Terminal add-on.

## Home Assistant Container (Docker)

SSH to the Docker host, not the container.

```bash
# Environment variables - adjust to your mount path
export HA_CONFIG_PATH="/opt/homeassistant/config"
export HA_STAGING_PATH="/opt/homeassistant/config_staging"

# SSH config
Host ha
  HostName your-docker-host
  User your-username
  Port 22
```

**Common mount paths:**
- `/opt/homeassistant/config`
- `/home/user/homeassistant`
- `/srv/homeassistant`

Check your `docker-compose.yml` for the exact path.

## Home Assistant Core

Direct Python installation.

```bash
# Environment variables
export HA_CONFIG_PATH="/home/homeassistant/.homeassistant"
export HA_STAGING_PATH="/home/homeassistant/.homeassistant_staging"

# SSH config
Host ha
  HostName your-server
  User homeassistant
  Port 22
```

## Home Assistant Supervised

Like HA OS but on custom OS.

```bash
# Environment variables (same as HA OS)
export HA_CONFIG_PATH="/homeassistant"
export HA_STAGING_PATH="/homeassistant/config_staging"

# SSH config
Host ha
  HostName your-server
  User your-username
  Port 22
```

## Detecting Your Installation Type

In Home Assistant:
1. Settings → About
2. Look at **Installation Type**

Or via API:
```bash
curl -s "$HOMEASSISTANT_URL/api/config" \
  -H "Authorization: Bearer $HOMEASSISTANT_TOKEN" \
  | jq '.installation_type'
```

## Path Discovery

If unsure of your config path:

```bash
# For HA OS / Supervised
ssh ha "ls /homeassistant"

# For Container (on Docker host)
docker exec homeassistant ls /config

# For Core
ssh ha "ls ~/.homeassistant"
```

## Creating Staging Directory

The staging directory needs to be created once:

```bash
# HA OS / Supervised
ssh ha "mkdir -p /homeassistant/config_staging"

# Container (on Docker host)
mkdir -p /opt/homeassistant/config_staging

# Core
ssh ha "mkdir -p ~/.homeassistant_staging"
```

Or use the init script which creates it automatically:

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/init-config.py
```
