# 🚀 kahl-dev Claude Marketplace

Claude Code plugins for home automation and productivity.

## 📦 Available Plugins

| Plugin | Description | Category |
|--------|-------------|----------|
| **[homeassistant](plugins/homeassistant/)** | Home Assistant control & config deployment | Smart Home |

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/kahl-dev/kahl-dev-claude-marketplace.git ~/repos/kahl-dev-claude-marketplace
~/repos/kahl-dev-claude-marketplace/scripts/install-local.sh
```

### 2. Set Environment Variables

```bash
# In ~/.zshrc or ~/.bashrc

# Home Assistant
export HOMEASSISTANT_URL="http://homeassistant.local:8123"
export HOMEASSISTANT_TOKEN="<your-long-lived-token>"
export HA_SSH_HOST="<your-ssh-alias>"  # For config deployment
```

### 3. Restart Claude Code

```bash
exit    # if in Claude
claude  # fresh start
```

### 4. Verify

```
/plugin  # should show homeassistant@kahl-dev-claude-marketplace
```

## 🔄 Updating

```bash
cd ~/repos/kahl-dev-claude-marketplace && git pull
```

Changes take effect on next Claude Code restart.

## 🔧 Troubleshooting

### Skills not appearing?

Run the symlink script:

```bash
~/repos/kahl-dev-claude-marketplace/scripts/symlink-skills.sh --local
```

### Plugin not working?

1. Check env vars are set: `echo $HOMEASSISTANT_URL`
2. Restart Claude: `exit` then `claude`
3. Check plugin enabled: `/plugin`

## 📖 Architecture

This marketplace uses the **Beyond MCP** pattern:

- **90%+ context savings** vs traditional MCP servers
- Self-contained Python scripts with UV inline dependencies
- Progressive disclosure (SKILL.md guides → scripts)
- No background processes or servers

See [docs/beyond-mcp.md](docs/beyond-mcp.md) for details.

## ⚠️ Known Claude Code Bugs

Skills from non-GitHub marketplaces need symlinks due to path resolution bugs:

| Bug | Issue | Workaround |
|-----|-------|------------|
| Skills wrong path | [#10113](https://github.com/anthropics/claude-code/issues/10113) | Symlinks in `~/.claude/skills/` |
| Commands not discovered | [#14929](https://github.com/anthropics/claude-code/issues/14929) | Symlinks in `~/.claude/commands/` |

The install script handles these automatically.

## 📂 Structure

```
kahl-dev-claude-marketplace/
├── .claude-plugin/
│   └── marketplace.json    # Marketplace definition
├── plugins/
│   └── homeassistant/      # Home Assistant plugin
│       ├── skills/
│       │   └── homeassistant/
│       │       ├── SKILL.md
│       │       └── scripts/  # 22 Python scripts
│       ├── docs/
│       └── README.md
├── scripts/
│   ├── install-local.sh    # One-line installer
│   └── symlink-skills.sh   # Symlink workaround
├── docs/
│   └── beyond-mcp.md       # Architecture docs
└── README.md
```

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## 🔒 Security

See [SECURITY.md](SECURITY.md) for:
- Required token scopes
- SSH security considerations
- Threat model

## 📝 License

MIT - See [LICENSE](LICENSE)

## 👤 Author

Patrick Kahl ([@kahl-dev](https://github.com/kahl-dev))
