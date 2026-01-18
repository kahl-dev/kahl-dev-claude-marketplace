#!/bin/bash
# =============================================================================
# Symlink kahl-dev-claude-marketplace skills to ~/.claude/skills/
# This makes them appear as (user) skills in Claude Code
#
# Why is this needed?
#   Claude Code has a known bug where skills from marketplace plugins are not
#   discovered correctly for non-GitHub installations:
#   - Skills: https://github.com/anthropics/claude-code/issues/10113
#
# Usage:
#   ./scripts/symlink-skills.sh           # Auto-detect
#   ./scripts/symlink-skills.sh --local   # Force local repo mode
#   ./scripts/symlink-skills.sh --clean   # Remove all symlinks
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
SKILLS_DIR="$HOME/.claude/skills"

# Parse arguments
MODE="auto"
CLEAN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --local)
            MODE="local"
            shift
            ;;
        --clean)
            CLEAN=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--local|--clean]"
            echo ""
            echo "Options:"
            echo "  --local   Force using local repo directory"
            echo "  --clean   Remove all kahl-dev-claude-marketplace symlinks"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Clean mode
if [ "$CLEAN" = true ]; then
    echo -e "${BLUE}Cleaning kahl-dev-claude-marketplace symlinks...${NC}"
    echo ""

    count=0
    if [ -d "$SKILLS_DIR" ]; then
        for link in "$SKILLS_DIR"/*; do
            if [ -L "$link" ]; then
                target=$(readlink "$link")
                if [[ "$target" == *"kahl-dev-claude-marketplace"* ]] || [[ "$target" == *"kahl-dev-claude-marketplace"* ]]; then
                    rm "$link"
                    echo -e "  ${GREEN}Removed:${NC} $(basename "$link")"
                    ((count++)) || true
                fi
            fi
        done
    fi

    echo ""
    echo -e "${GREEN}Done!${NC} Removed $count symlinks."
    exit 0
fi

# Create directory if needed
mkdir -p "$SKILLS_DIR"

# Counters
skills_count=0
skipped=0

# Function to create skill symlinks
symlink_plugin_skills() {
    local plugin_dir="$1"
    local plugin_name="$2"

    if [ -d "$plugin_dir/skills" ]; then
        for skill_dir in "$plugin_dir/skills"/*/; do
            [ -d "$skill_dir" ] || continue

            skill_dir="${skill_dir%/}"
            skill_name=$(basename "$skill_dir")
            target="$SKILLS_DIR/$skill_name"

            # Handle existing targets
            if [ -L "$target" ]; then
                rm "$target"
            elif [ -d "$target" ]; then
                echo -e "  ${YELLOW}SKIP:${NC} $skill_name (real directory exists)"
                ((skipped++)) || true
                continue
            elif [ -e "$target" ]; then
                echo -e "  ${YELLOW}SKIP:${NC} $skill_name (file exists)"
                ((skipped++)) || true
                continue
            fi

            # Create symlink
            if ln -sf "$skill_dir" "$target" 2>/dev/null; then
                echo -e "  ${GREEN}skill:${NC} $skill_name -> $plugin_name"
                ((skills_count++)) || true
            fi
        done
    fi
}

# Local mode
if [ "$MODE" = "local" ] || [ -d "$REPO_DIR/plugins" ]; then
    if [ ! -d "$REPO_DIR/plugins" ]; then
        echo -e "${RED}Error: plugins directory not found at $REPO_DIR/plugins${NC}"
        exit 1
    fi

    echo -e "${BLUE}Mode:${NC} Local repository"
    echo -e "${BLUE}Source:${NC} $REPO_DIR/plugins"
    echo -e "${BLUE}Target:${NC} $SKILLS_DIR"
    echo ""
    echo "Symlinking skills..."
    echo ""

    for plugin_dir in "$REPO_DIR/plugins"/*/; do
        [ -d "$plugin_dir" ] || continue
        plugin_dir="${plugin_dir%/}"
        plugin_name=$(basename "$plugin_dir")
        symlink_plugin_skills "$plugin_dir" "$plugin_name"
    done
fi

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}Skills:${NC} $skills_count symlinked"
[ "$skipped" -gt 0 ] && echo -e "${YELLOW}Skipped:${NC} $skipped items"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ "$skills_count" -gt 0 ]; then
    echo -e "${GREEN}Success!${NC} Restart Claude Code to see changes."
else
    echo -e "${YELLOW}Nothing symlinked.${NC}"
fi
