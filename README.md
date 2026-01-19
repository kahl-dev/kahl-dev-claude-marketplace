# kahl-dev Claude Marketplace

Claude Code plugins for home automation and productivity.

> **⚠️ Use at your own risk.** This software can modify your Home Assistant configuration. Always maintain backups. See [LICENSE](LICENSE) for warranty disclaimer.

## Available Plugins

| Plugin | Description | Category |
|--------|-------------|----------|
| [homeassistant](plugins/homeassistant/) | Home Assistant control & config deployment | Smart Home |

## Install

Add the marketplace to Claude Code:

```
/plugin marketplace add https://github.com/kahl-dev/kahl-dev-claude-marketplace
```

Install the Home Assistant plugin:

```
/plugin install homeassistant
```

Or browse available plugins via the UI:

```
/plugin
```

Navigate to **Discover** tab and select plugins to install.

## Configuration

The Home Assistant plugin requires environment variables. Add to `~/.zshrc` or `~/.bashrc`:

```bash
# Required - Home Assistant API access
export HOMEASSISTANT_URL="http://homeassistant.local:8123"
export HOMEASSISTANT_TOKEN="<your-long-lived-token>"

# Required for config deployment
export HA_SSH_HOST="<your-ssh-alias>"

# Optional (has default)
export HA_LOCAL_CONFIG="~/ha-config"
```

Restart your shell or run `source ~/.zshrc`, then restart Claude Code.

## Usage

After installation, the `homeassistant` skill is available. Example commands:

```bash
# List entities
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/list-entities.py --domain light

# Deploy config changes
uv run ${CLAUDE_PLUGIN_ROOT}/skills/homeassistant/scripts/deploy-config.py
```

See [plugins/homeassistant/README.md](plugins/homeassistant/README.md) for complete documentation.

## Updating

Update the marketplace via Claude Code:

```
/plugin
```

Navigate to **Marketplaces** tab → select `kahl-dev-claude-marketplace` → **Update marketplace**.

## Architecture

This marketplace uses the **Beyond MCP** pattern:

- **90%+ context savings** compared to traditional MCP servers
- Self-contained Python scripts with UV inline dependencies
- Progressive disclosure (SKILL.md guides Claude to scripts)
- No background processes or servers

See [docs/beyond-mcp.md](docs/beyond-mcp.md) for details.

## Structure

```
kahl-dev-claude-marketplace/
├── .claude-plugin/
│   └── marketplace.json
├── plugins/
│   └── homeassistant/
│       ├── skills/homeassistant/
│       │   ├── SKILL.md
│       │   └── scripts/
│       ├── docs/
│       └── README.md
├── docs/
│   └── beyond-mcp.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md
└── SECURITY.md
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

See [SECURITY.md](SECURITY.md) for:

- Required token scopes
- SSH security considerations
- Threat model

## License

MIT - See [LICENSE](LICENSE)

## Author

Patrick Kahl ([@kahl-dev](https://github.com/kahl-dev))
