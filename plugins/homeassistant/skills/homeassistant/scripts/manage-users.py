#!/usr/bin/env python3
# /// script
# dependencies = [
#     "click>=8.1.7",
#     "websocket-client>=1.9.0",
# ]
# ///

"""
Home Assistant User Management Script

List, create, and delete users via WebSocket API.

Usage:
    uv run manage-users.py list
    uv run manage-users.py create --name "Guest" --username guest
    uv run manage-users.py delete --user-id abc123 --confirm
    uv run manage-users.py --help

Note: User creation requires setting a password through the HA UI or
      using the auth provider's method. This script creates the user
      record but password must be set separately.
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


# Configuration from environment
HA_URL = get_required_env(
    "HOMEASSISTANT_URL",
    "Your HA instance URL, e.g., http://homeassistant.local:8123",
)
HA_TOKEN = get_required_env(
    "HOMEASSISTANT_TOKEN",
    "Get from: HA → Profile → Security → Long-Lived Access Tokens",
)
WS_TIMEOUT = 30


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


def format_users(users: list[dict[str, Any]]) -> str:
    """Format users for human-readable output."""
    lines: list[str] = []

    if not users:
        return "No users found."

    lines.append("")
    lines.append("=" * 60)
    lines.append("👤 Home Assistant Users")
    lines.append("=" * 60)

    for user in sorted(users, key=lambda x: x.get("name", "")):
        user_id = user.get("id", "")
        name = user.get("name", "")
        username = user.get("username", "")
        is_owner = user.get("is_owner", False)
        is_active = user.get("is_active", True)
        system_generated = user.get("system_generated", False)
        local_only = user.get("local_only", False)
        group_ids = user.get("group_ids", [])

        # Role/type indicator
        if system_generated:
            role = "🤖 System"
        elif is_owner:
            role = "👑 Owner"
        elif "system-admin" in group_ids:
            role = "🔧 Admin"
        else:
            role = "👤 User"

        # Status indicator
        if not is_active:
            status = "⏸️ Inactive"
        elif local_only:
            status = "🏠 Local only"
        else:
            status = "✅ Active"

        lines.append("")
        lines.append(f"{role} {name}")
        lines.append(f"   ID: {user_id}")
        if username:
            lines.append(f"   Username: {username}")
        lines.append(f"   Status: {status}")
        if group_ids:
            lines.append(f"   Groups: {', '.join(group_ids)}")

    lines.append("")
    lines.append("-" * 60)
    lines.append(f"Total: {len(users)} users")
    lines.append("")

    return "\n".join(lines)


@click.group()
def cli() -> None:
    """Manage Home Assistant users (list, create, delete)."""
    pass


@cli.command("list")
@click.option("--active-only", is_flag=True, help="Show only active users")
@click.option("--exclude-system", is_flag=True, help="Exclude system-generated users")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def list_users(active_only: bool, exclude_system: bool, output_json: bool) -> None:
    """List all users."""
    try:
        result = websocket_command("config/auth/list")
        users = result if isinstance(result, list) else []

        # Apply filters
        if active_only:
            users = [u for u in users if u.get("is_active", True)]
        if exclude_system:
            users = [u for u in users if not u.get("system_generated", False)]

        if output_json:
            click.echo(json.dumps(users, indent=2))
        else:
            formatted = format_users(users)
            click.echo(formatted)

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--name", required=True, help="Display name for the user")
@click.option("--admin", is_flag=True, help="Make user an administrator")
@click.option("--local-only", is_flag=True, help="Restrict user to local access only")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def create(
    name: str,
    admin: bool,
    local_only: bool,
    output_json: bool,
) -> None:
    """
    Create a new user (without login credentials).

    Note: Login credentials (username/password) must be configured
    through the Home Assistant UI after user creation.
    """
    try:
        # Determine group
        group_ids = ["system-admin"] if admin else ["system-users"]

        params: dict[str, Any] = {
            "name": name,
            "group_ids": group_ids,
            "local_only": local_only,
        }

        result = websocket_command("config/auth/create", params)

        if output_json:
            click.echo(json.dumps(result, indent=2))
        else:
            user = result.get("user", result)
            user_id = user.get("id", "")
            role = "administrator" if admin else "user"
            click.echo(f"✅ Created {role}: {name} (ID: {user_id})")
            click.echo("   Note: Set login credentials via HA UI → Settings → People")

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--user-id", required=True, help="User ID to delete (get from list --json)")
@click.option("--confirm", is_flag=True, help="Confirm destructive operation")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def delete(user_id: str, confirm: bool, output_json: bool) -> None:
    """Delete a user (requires --confirm)."""
    try:
        if not confirm:
            click.echo("⚠️  This will permanently delete the user.", err=True)
            click.echo("   All associated credentials and tokens will be revoked.", err=True)
            click.echo("   Run with --confirm to proceed.", err=True)
            sys.exit(1)

        websocket_command("config/auth/delete", {"user_id": user_id})

        if output_json:
            click.echo(json.dumps({"deleted": user_id}, indent=2))
        else:
            click.echo(f"✅ Deleted user: {user_id}")

        sys.exit(0)

    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
