# Installation Guide

## Prerequisites

- **Python 3.11+**
- **[uv](https://github.com/astral-sh/uv)** - Modern Python package runner
- **Home Assistant 2024.x+** (tested with 2025.x)
- **SSH access** (for config deployment features)

## Step 1: Install the Plugin

In Claude Code, add the marketplace and install the plugin:

```
/plugin marketplace add kahl-dev/kahl-dev-claude-marketplace
/plugin install homeassistant@kahl-dev-claude-marketplace
```

Or browse available plugins via the UI:

```
/plugin
```

Navigate to **Discover** tab and select `homeassistant` to install.

## Step 2: Create Home Assistant Token

1. Open Home Assistant web interface
2. Click your profile (bottom left)
3. Go to **Security** tab
4. Scroll to **Long-Lived Access Tokens**
5. Click **Create Token**
6. Name it "Claude Code" (or similar)
7. **Copy the token immediately** (you won't see it again!)

## Step 3: Set Environment Variables

Add to `~/.zshrc` (or `~/.bashrc`):

```bash
# Home Assistant - Required for all operations
export HOMEASSISTANT_URL="http://homeassistant.local:8123"
export HOMEASSISTANT_TOKEN="<paste-your-token-here>"

# SSH - Required for config deployment
export HA_SSH_HOST="<your-ssh-alias>"

# Optional - Override defaults
# export HA_LOCAL_CONFIG="~/ha-config"
# export HA_CONFIG_PATH="/homeassistant"
# export HA_STAGING_PATH="/homeassistant/config_staging"
```

Then reload:

```bash
source ~/.zshrc
```

## Step 4: Verify Installation

Restart Claude Code and test:

```bash
exit   # if in Claude
claude # fresh start
```

In Claude, ask:
> "List my Home Assistant entities"

Or run directly:

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/get-config.py
```

## Step 5: SSH Setup (Optional)

If you want to deploy config changes, see [SSH Setup](ssh-setup.md).

## Troubleshooting

### "Skill not found"

Reinstall the plugin:

```
/plugin install homeassistant
```

Or check that the marketplace is properly added:

```
/plugin
```

Navigate to **Marketplaces** tab to verify `kahl-dev-claude-marketplace` is listed.

### "Connection refused"

Check your Home Assistant URL:

```bash
curl -s "$HOMEASSISTANT_URL/api/" -H "Authorization: Bearer $HOMEASSISTANT_TOKEN"
```

Should return: `{"message": "API running."}`

### "401 Unauthorized"

Your token is invalid or expired. Create a new one in HA.

### "Cannot connect to SSH"

See [SSH Setup](ssh-setup.md) for detailed SSH configuration.
