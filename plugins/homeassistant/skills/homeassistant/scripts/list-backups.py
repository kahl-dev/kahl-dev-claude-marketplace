#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
# ]
# ///

"""
Home Assistant List Backups Script

List all available backups via REST API.

Usage:
    uv run list-backups.py
    uv run list-backups.py --json
    uv run list-backups.py --help
"""

import json
import os
import sys
from typing import Any

import click
import httpx


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
API_TIMEOUT = 30.0
USER_AGENT = "HomeAssistant-CLI/1.0"


def format_size(size_bytes: int) -> str:
    """Format bytes as human-readable size."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def format_backups(backups: list[dict[str, Any]], backing_up: bool) -> str:
    """Format backups for human-readable output."""
    lines: list[str] = []

    lines.append("")
    lines.append("=" * 70)
    lines.append("💾 Home Assistant Backups")
    lines.append("=" * 70)

    if backing_up:
        lines.append("")
        lines.append("⏳ Backup in progress...")

    if not backups:
        lines.append("")
        lines.append("No backups found.")
        lines.append("")
        return "\n".join(lines)

    for backup in sorted(backups, key=lambda x: x.get("date", ""), reverse=True):
        backup_id = backup.get("backup_id", backup.get("slug", ""))
        name = backup.get("name", "(unnamed)")
        date = backup.get("date", "")
        size = backup.get("size", 0)
        backup_type = backup.get("type", "unknown")
        protected = backup.get("protected", False)

        # Format date
        if date:
            date_display = date[:19].replace("T", " ")
        else:
            date_display = "Unknown date"

        # Type indicator
        if backup_type == "full":
            type_icon = "📦"
            type_text = "Full"
        elif backup_type == "partial":
            type_icon = "📁"
            type_text = "Partial"
        else:
            type_icon = "❓"
            type_text = backup_type

        lines.append("")
        lines.append(f"{type_icon} {name}")
        lines.append(f"   ID: {backup_id}")
        lines.append(f"   Date: {date_display}")
        lines.append(f"   Size: {format_size(size)}")
        lines.append(f"   Type: {type_text}")
        if protected:
            lines.append("   🔒 Password protected")

    lines.append("")
    lines.append("-" * 70)
    lines.append(f"Total: {len(backups)} backups")
    lines.append("")

    return "\n".join(lines)


@click.command()
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def main(output_json: bool) -> None:
    """
    List all Home Assistant backups.

    Examples:

        uv run list-backups.py

        uv run list-backups.py --json
    """
    try:
        with httpx.Client(
            base_url=f"{HA_URL}/api",
            headers={
                "Authorization": f"Bearer {HA_TOKEN}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
            timeout=API_TIMEOUT,
        ) as client:
            response = client.get("/backup/info")
            response.raise_for_status()
            data = response.json()

        backups = data.get("backups", [])
        backing_up = data.get("backing_up", False)

        if output_json:
            click.echo(json.dumps(data, indent=2))
        else:
            formatted = format_backups(backups, backing_up)
            click.echo(formatted)

        sys.exit(0)

    except httpx.HTTPStatusError as error:
        if error.response.status_code == 404:
            # Backup API not available - requires Supervisor (HassOS)
            if output_json:
                click.echo(
                    json.dumps(
                        {
                            "error": "Backup API not available",
                            "message": "Backup REST API requires Home Assistant OS or Supervised installation",
                        },
                        indent=2,
                    )
                )
            else:
                click.echo("❌ Backup API not available", err=True)
                click.echo("   This endpoint requires Home Assistant OS or Supervised installation.", err=True)
                click.echo("   For HA Core installations, backups are managed differently.", err=True)
            sys.exit(1)

        error_msg = f"HTTP {error.response.status_code}"
        try:
            error_detail = error.response.json()
            error_msg = error_detail.get("message", error_msg)
        except Exception:
            pass
        if output_json:
            click.echo(json.dumps({"error": error_msg}, indent=2))
        else:
            click.echo(f"❌ Error: {error_msg}", err=True)
        sys.exit(1)
    except Exception as error:
        if output_json:
            click.echo(json.dumps({"error": str(error)}, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
