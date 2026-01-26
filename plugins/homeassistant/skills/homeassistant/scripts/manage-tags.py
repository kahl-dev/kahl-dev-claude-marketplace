#!/usr/bin/env python3
# /// script
# dependencies = [
#     "click>=8.1.7",
#     "websocket-client>=1.9.0",
# ]
# ///

"""
Home Assistant Tag Management Script

List, create, update, and delete NFC/QR tags via WebSocket API.

Usage:
    uv run manage-tags.py list
    uv run manage-tags.py create --name "Front Door" --tag-id custom_tag_123
    uv run manage-tags.py update --tag-id abc123 --name "Back Door"
    uv run manage-tags.py delete --tag-id abc123 --confirm
    uv run manage-tags.py --help
"""

import json
import os
import sys
from typing import Any
from urllib.parse import urlparse, urlunparse

import click
from websocket import WebSocketTimeoutException, create_connection


def get_required_env(name: str, help_text: str = "") -> str:
    """Get required environment variable or fail fast."""
    value = os.getenv(name)
    if not value:
        click.echo(f"❌ Error: {name} not set.", err=True)
        if help_text:
            click.echo(f"   {help_text}", err=True)
        click.echo(f'   Set: export {name}="<value>"', err=True)
        sys.exit(1)
    return value


# Configuration from environment (validated at runtime for --help support)
HA_URL: str = ""
HA_TOKEN: str = ""
WS_TIMEOUT = 30


def _validate_config() -> None:
    """Validate required environment variables."""
    global HA_URL, HA_TOKEN
    HA_URL = get_required_env(
        "HOMEASSISTANT_URL",
        "Your HA instance URL, e.g., http://homeassistant.local:8123",
    )
    HA_TOKEN = get_required_env(
        "HOMEASSISTANT_TOKEN",
        "Get from: HA → Profile → Security → Long-Lived Access Tokens",
    )


def get_websocket_url(base_url: str) -> str:
    """Convert HTTP(S) URL to WebSocket URL using proper parsing."""
    parsed = urlparse(base_url)
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    base_path = parsed.path.rstrip("/")
    ws_path = f"{base_path}/api/websocket"
    return urlunparse(parsed._replace(scheme=ws_scheme, path=ws_path))


def websocket_command(command_type: str, params: dict[str, Any] | None = None) -> Any:
    """Execute WebSocket command and return result."""
    ws_url = get_websocket_url(HA_URL)
    ws = None
    try:
        ws = create_connection(ws_url, timeout=WS_TIMEOUT)
        # Auth phase
        ws.recv()  # auth_required
        ws.send(json.dumps({"type": "auth", "access_token": HA_TOKEN}))
        auth_result = json.loads(ws.recv())

        if auth_result.get("type") != "auth_ok":
            raise Exception(f"Authentication failed: {auth_result}")

        # Command phase
        message: dict[str, Any] = {"id": 1, "type": command_type}
        if params:
            message.update(params)
        ws.send(json.dumps(message))
        result = json.loads(ws.recv())

        if not result.get("success"):
            error = result.get("error", {})
            error_code = error.get("code", "unknown")
            if error_code == "unknown_command":
                raise Exception(f"Command '{command_type}' not supported (HA version may be incompatible)")
            raise Exception(f"Command failed: {error.get('message', 'Unknown error')}")

        return result.get("result", {})
    except WebSocketTimeoutException as error:
        raise Exception(f"WebSocket timeout after {WS_TIMEOUT}s") from error
    finally:
        if ws:
            ws.close()


def format_tags(tags: list[dict[str, Any]]) -> str:
    """Format tags for human-readable output."""
    lines: list[str] = []

    if not tags:
        return "No tags found."

    lines.append("")
    lines.append("=" * 60)
    lines.append("🏷️  Home Assistant Tags (NFC/QR)")
    lines.append("=" * 60)

    for tag in sorted(tags, key=lambda x: x.get("name", "") or x.get("tag_id", "")):
        tag_id = tag.get("tag_id", "") or tag.get("id", "")
        name = tag.get("name", "") or "(unnamed)"
        last_scanned = tag.get("last_scanned", "")
        description = tag.get("description", "")

        lines.append("")
        lines.append(f"🏷️  {name}")
        lines.append(f"   Tag ID: {tag_id}")
        if description:
            lines.append(f"   Description: {description}")
        if last_scanned:
            lines.append(f"   Last scanned: {last_scanned}")

    lines.append("")
    lines.append("-" * 60)
    lines.append(f"Total: {len(tags)} tags")
    lines.append("")

    return "\n".join(lines)


@click.group()
def cli() -> None:
    """Manage Home Assistant NFC/QR tags (list, create, update, delete)."""
    pass


@cli.command("list")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def list_tags(output_json: bool) -> None:
    """List all tags."""
    _validate_config()
    try:
        result = websocket_command("tag/list")
        tags = result if isinstance(result, list) else []

        if output_json:
            click.echo(json.dumps(tags, indent=2))
        else:
            formatted = format_tags(tags)
            click.echo(formatted)

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--tag-id", required=True, type=str, help="Tag ID (required - HA does not auto-generate)")
@click.option("--name", type=str, help="Tag name")
@click.option("--description", type=str, help="Tag description")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def create(
    tag_id: str | None,
    name: str | None,
    description: str | None,
    output_json: bool,
) -> None:
    """Create a new tag."""
    try:
        params: dict[str, Any] = {}
        if tag_id:
            params["tag_id"] = tag_id
        if name:
            params["name"] = name
        if description:
            params["description"] = description

        result = websocket_command("tag/create", params)

        if output_json:
            click.echo(json.dumps(result, indent=2))
        else:
            created_id = result.get("tag_id", result.get("id", ""))
            display_name = name or created_id
            click.echo(f"✅ Created tag: {display_name} (ID: {created_id})")

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--tag-id", required=True, help="Tag ID to update")
@click.option("--name", type=str, help="New name")
@click.option("--description", type=str, help="New description (empty to remove)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def update(
    tag_id: str,
    name: str | None,
    description: str | None,
    output_json: bool,
) -> None:
    """Update an existing tag."""
    try:
        params: dict[str, Any] = {"tag_id": tag_id}

        if name is not None:
            params["name"] = name
        if description is not None:
            params["description"] = description if description != "" else None

        result = websocket_command("tag/update", params)

        if output_json:
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"✅ Updated tag: {tag_id}")

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--tag-id", required=True, help="Tag ID to delete")
@click.option("--confirm", is_flag=True, help="Confirm destructive operation")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def delete(
    tag_id: str,
    confirm: bool,
    output_json: bool,
) -> None:
    """Delete a tag (requires --confirm)."""
    try:
        if not confirm:
            click.echo("⚠️  This will permanently delete the tag.", err=True)
            click.echo("   Automations triggered by this tag may break.", err=True)
            click.echo("   Run with --confirm to proceed.", err=True)
            sys.exit(1)

        params: dict[str, Any] = {"tag_id": tag_id}
        websocket_command("tag/delete", params)

        if output_json:
            click.echo(json.dumps({"deleted": tag_id}, indent=2))
        else:
            click.echo(f"✅ Deleted tag: {tag_id}")

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
