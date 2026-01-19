#!/bin/bash
# 🔢 Bump plugin version
# Usage: ./scripts/bump-version.sh <plugin-name> <major|minor|patch>

set -e

PLUGIN=$1
BUMP_TYPE=$2

if [ -z "$PLUGIN" ] || [ -z "$BUMP_TYPE" ]; then
    echo "Usage: $0 <plugin-name> <major|minor|patch>"
    echo "Example: ./scripts/bump-version.sh homeassistant patch"
    exit 1
fi

PLUGIN_JSON="plugins/$PLUGIN/.claude-plugin/plugin.json"

if [ ! -f "$PLUGIN_JSON" ]; then
    echo "❌ Plugin not found: $PLUGIN"
    echo "   Expected: $PLUGIN_JSON"
    exit 1
fi

CURRENT=$(jq -r '.version' "$PLUGIN_JSON")
echo "📦 Plugin: $PLUGIN"
echo "   Current version: $CURRENT"

IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"

case $BUMP_TYPE in
    major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
    minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
    patch) PATCH=$((PATCH + 1)) ;;
    *) echo "❌ Invalid bump type: $BUMP_TYPE (use major|minor|patch)"; exit 1 ;;
esac

NEW_VERSION="$MAJOR.$MINOR.$PATCH"
echo "   New version: $NEW_VERSION"

jq ".version = \"$NEW_VERSION\"" "$PLUGIN_JSON" > "$PLUGIN_JSON.tmp"
mv "$PLUGIN_JSON.tmp" "$PLUGIN_JSON"

echo ""
echo "✅ Updated $PLUGIN to $NEW_VERSION"
echo ""
echo "Next steps:"
echo "  1. Update CHANGELOG.md"
echo "  2. git add -A && git commit -m \"chore($PLUGIN): bump to $NEW_VERSION\""
