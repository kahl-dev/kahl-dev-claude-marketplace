#!/usr/bin/env python3
# /// script
# dependencies = [
#     "click>=8.1.7",
#     "websocket-client>=1.9.0",
# ]
# ///

"""
Home Assistant Person Management Script

List, create, update, and delete persons via WebSocket API.

Usage:
    uv run manage-persons.py list
    uv run manage-persons.py create --name "John Doe" --user-id abc123
    uv run manage-persons.py update --person-id john_doe --name "John Smith"
    uv run manage-persons.py delete --person-id john_doe --confirm
    uv run manage-persons.py --help
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


def format_persons(persons: list[dict[str, Any]]) -> str:
    """Format persons for human-readable output."""
    lines: list[str] = []

    if not persons:
        return "No persons found."

    lines.append("")
    lines.append("=" * 60)
    lines.append("👤 Home Assistant Persons")
    lines.append("=" * 60)

    for person in sorted(persons, key=lambda x: x.get("name", "")):
        person_id = person.get("id", "")
        name = person.get("name", "")
        user_id = person.get("user_id", "")
        device_trackers = person.get("device_trackers", [])
        picture = person.get("picture", "")

        lines.append("")
        lines.append(f"👤 {name}")
        lines.append(f"   ID: {person_id}")
        if user_id:
            lines.append(f"   User ID: {user_id}")
        if device_trackers:
            lines.append(f"   Trackers: {', '.join(device_trackers)}")
        if picture:
            lines.append(f"   Picture: {picture}")

    lines.append("")
    lines.append("-" * 60)
    lines.append(f"Total: {len(persons)} persons")
    lines.append("")

    return "\n".join(lines)


@click.group()
def cli() -> None:
    """Manage Home Assistant persons (list, create, update, delete)."""
    pass


@cli.command("list")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def list_persons(output_json: bool) -> None:
    """List all persons."""
    _validate_config()
    try:
        result = websocket_command("person/list")
        persons = result.get("storage", []) if isinstance(result, dict) else []

        if output_json:
            click.echo(json.dumps(persons, indent=2))
        else:
            formatted = format_persons(persons)
            click.echo(formatted)

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--name", required=True, help="Person name")
@click.option("--user-id", type=str, help="Associated HA user ID")
@click.option("--device-trackers", type=str, help="Comma-separated device tracker entity IDs")
@click.option("--picture", type=str, help="Picture URL or path")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def create(
    name: str,
    user_id: str | None,
    device_trackers: str | None,
    picture: str | None,
    output_json: bool,
) -> None:
    """Create a new person."""
    try:
        params: dict[str, Any] = {"name": name}
        if user_id:
            params["user_id"] = user_id
        if device_trackers:
            params["device_trackers"] = [dt.strip() for dt in device_trackers.split(",")]
        if picture:
            params["picture"] = picture

        result = websocket_command("person/create", params)

        if output_json:
            click.echo(json.dumps(result, indent=2))
        else:
            person_id = result.get("id", "")
            click.echo(f"✅ Created person: {name} (ID: {person_id})")

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--person-id", required=True, help="Person ID to update")
@click.option("--name", type=str, help="New name")
@click.option("--user-id", type=str, help="New user ID (empty to remove)")
@click.option("--device-trackers", type=str, help="New comma-separated device trackers (replaces existing)")
@click.option("--picture", type=str, help="New picture (empty to remove)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def update(
    person_id: str,
    name: str | None,
    user_id: str | None,
    device_trackers: str | None,
    picture: str | None,
    output_json: bool,
) -> None:
    """Update an existing person."""
    try:
        params: dict[str, Any] = {"person_id": person_id}

        if name is not None:
            params["name"] = name
        if user_id is not None:
            params["user_id"] = user_id if user_id != "" else None
        if device_trackers is not None:
            params["device_trackers"] = [dt.strip() for dt in device_trackers.split(",")] if device_trackers else []
        if picture is not None:
            params["picture"] = picture if picture != "" else None

        result = websocket_command("person/update", params)

        if output_json:
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"✅ Updated person: {person_id}")

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--person-id", required=True, help="Person ID to delete")
@click.option("--confirm", is_flag=True, help="Confirm destructive operation")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def delete(
    person_id: str,
    confirm: bool,
    output_json: bool,
) -> None:
    """Delete a person (requires --confirm)."""
    try:
        if not confirm:
            click.echo("⚠️  This will permanently delete the person.", err=True)
            click.echo("   Run with --confirm to proceed.", err=True)
            sys.exit(1)

        params: dict[str, Any] = {"person_id": person_id}
        websocket_command("person/delete", params)

        if output_json:
            click.echo(json.dumps({"deleted": person_id}, indent=2))
        else:
            click.echo(f"✅ Deleted person: {person_id}")

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
