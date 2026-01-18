#!/bin/bash
# 🚀 kahl-dev Claude Marketplace - Local Installation Script
#
# Usage:
#   git clone https://github.com/kahl-dev/kahl-dev-claude-marketplace.git ~/repos/kahl-dev-claude-marketplace
#   ~/repos/kahl-dev-claude-marketplace/scripts/install-local.sh
#
# What this script does:
#   1. Configures marketplace as "directory" source
#   2. Installs all plugins
#   3. Creates skill symlinks (workaround for Claude Code bug)
#   4. Shows next steps

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEFAULT_INSTALL_PATH="$HOME/repos/kahl-dev-claude-marketplace"
MARKETPLACE_NAME="kahl-dev-claude-marketplace"
SETTINGS_FILE="$HOME/.claude/settings.local.json"

echo -e "${BLUE}🚀 kahl-dev Claude Marketplace - Local Installation${NC}"
echo ""

# Determine install path
if [[ -f ".claude-plugin/marketplace.json" ]]; then
    INSTALL_PATH="$(pwd)"
    echo -e "${GREEN}✓${NC} Using current directory: $INSTALL_PATH"
elif [[ -d "$DEFAULT_INSTALL_PATH/.git" ]]; then
    INSTALL_PATH="$DEFAULT_INSTALL_PATH"
    echo -e "${GREEN}✓${NC} Found existing repo: $INSTALL_PATH"
else
    echo -e "${RED}✗${NC} Marketplace not found"
    echo ""
    echo "Please clone first:"
    echo "  git clone https://github.com/kahl-dev/kahl-dev-claude-marketplace.git ~/repos/kahl-dev-claude-marketplace"
    exit 1
fi

echo ""

# Ensure .claude directory exists
mkdir -p "$HOME/.claude"

# Configure marketplace in settings.local.json
echo -e "${YELLOW}→${NC} Configuring marketplace..."

if [[ -f "$SETTINGS_FILE" ]] && command -v jq &> /dev/null; then
    TEMP_FILE=$(mktemp)
    jq --arg path "$INSTALL_PATH" '
        .extraKnownMarketplaces["kahl-dev-claude-marketplace"] = {
            "source": {
                "source": "directory",
                "path": $path
            }
        } |
        .enabledPlugins["homeassistant@kahl-dev-claude-marketplace"] = true
    ' "$SETTINGS_FILE" > "$TEMP_FILE" && mv "$TEMP_FILE" "$SETTINGS_FILE"
    echo -e "${GREEN}✓${NC} Updated $SETTINGS_FILE"
else
    cat > "$SETTINGS_FILE" << EOF
{
  "extraKnownMarketplaces": {
    "kahl-dev-claude-marketplace": {
      "source": {
        "source": "directory",
        "path": "$INSTALL_PATH"
      }
    }
  },
  "enabledPlugins": {
    "homeassistant@kahl-dev-claude-marketplace": true
  }
}
EOF
    echo -e "${GREEN}✓${NC} Created $SETTINGS_FILE"
fi

echo ""

# Update known_marketplaces.json
KNOWN_MARKETPLACES="$HOME/.claude/plugins/known_marketplaces.json"
if [[ -f "$KNOWN_MARKETPLACES" ]] && command -v jq &> /dev/null; then
    echo -e "${YELLOW}→${NC} Updating marketplace registry..."
    mkdir -p "$HOME/.claude/plugins"

    TEMP_FILE=$(mktemp)
    jq --arg path "$INSTALL_PATH" '
        .["kahl-dev-claude-marketplace"] = {
            "source": {
                "source": "directory",
                "path": $path
            },
            "installLocation": $path,
            "lastUpdated": (now | todate)
        }
    ' "$KNOWN_MARKETPLACES" > "$TEMP_FILE" && mv "$TEMP_FILE" "$KNOWN_MARKETPLACES"
    echo -e "${GREEN}✓${NC} Updated marketplace registry"
fi

echo ""

# Run symlink script
echo -e "${YELLOW}→${NC} Creating skill symlinks..."
if [[ -x "$INSTALL_PATH/scripts/symlink-skills.sh" ]]; then
    "$INSTALL_PATH/scripts/symlink-skills.sh" --local
else
    echo -e "${YELLOW}!${NC} symlink-skills.sh not found or not executable"
fi

echo ""

# Summary
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Installation complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "📂 Marketplace: ${BLUE}$INSTALL_PATH${NC}"
echo -e "⚙️  Settings:    ${BLUE}$SETTINGS_FILE${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo ""
echo "1. Set environment variables in ~/.zshrc:"
echo ""
echo "   # Home Assistant (required)"
echo "   export HOMEASSISTANT_URL=\"http://homeassistant.local:8123\""
echo "   export HOMEASSISTANT_TOKEN=\"<your-long-lived-token>\""
echo ""
echo "   # For config deployment (required for deploy-config.py)"
echo "   export HA_SSH_HOST=\"<your-ssh-alias>\"  # NO DEFAULT - must be set!"
echo ""
echo "   # Optional (have sensible defaults)"
echo "   export HA_LOCAL_CONFIG=\"~/ha-config\"   # Default: ~/ha-config"
echo ""
echo "2. Restart Claude Code:"
echo "   exit    # if currently in Claude"
echo "   claude  # start fresh session"
echo ""
echo "3. Verify installation:"
echo "   /plugin  # should show homeassistant@kahl-dev-claude-marketplace"
echo ""
echo -e "${BLUE}📚 Docs: $INSTALL_PATH/README.md${NC}"
