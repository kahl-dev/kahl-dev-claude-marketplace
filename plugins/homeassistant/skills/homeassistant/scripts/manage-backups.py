#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
# ]
# ///

"""
Home Assistant Backup Management Script

Restore and delete backups via REST API.

Usage:
    uv run manage-backups.py restore --backup-id abc123 --confirm
    uv run manage-backups.py delete --backup-id abc123 --confirm
    uv run manage-backups.py --help

Note: Use trigger-backup.py to create new backups.
"""

import json
import os
import sys

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
API_TIMEOUT = 300.0  # Restore can take a while
USER_AGENT = "HomeAssistant-CLI/1.0"


@click.group()
def cli() -> None:
    """Manage Home Assistant backups (restore, delete)."""
    pass


@cli.command()
@click.option("--backup-id", required=True, help="Backup ID to restore (get from list-backups.py --json)")
@click.option("--password", type=str, help="Password for encrypted backup")
@click.option("--confirm", is_flag=True, help="Confirm destructive operation")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def restore(
    backup_id: str,
    password: str | None,
    confirm: bool,
    output_json: bool,
) -> None:
    """
    Restore a backup.

    WARNING: This will restart Home Assistant and may overwrite current configuration!
    """
    try:
        if not confirm:
            click.echo("⚠️  This will restore the backup and restart Home Assistant.", err=True)
            click.echo("   Current configuration may be overwritten.", err=True)
            click.echo(f"   Backup ID: {backup_id}", err=True)
            click.echo("   Run with --confirm to proceed.", err=True)
            sys.exit(1)

        with httpx.Client(
            base_url=f"{HA_URL}/api",
            headers={
                "Authorization": f"Bearer {HA_TOKEN}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
            timeout=API_TIMEOUT,
        ) as client:
            # Build restore payload
            payload = {}
            if password:
                payload["password"] = password

            response = client.post(
                f"/backup/restore/{backup_id}",
                json=payload if payload else None,
            )
            response.raise_for_status()

        if output_json:
            click.echo(
                json.dumps(
                    {
                        "restored": backup_id,
                        "message": "Restore initiated. Home Assistant will restart.",
                    },
                    indent=2,
                )
            )
        else:
            click.echo(f"✅ Restore initiated: {backup_id}")
            click.echo("   Home Assistant will restart shortly.")

        sys.exit(0)

    except httpx.HTTPStatusError as error:
        if error.response.status_code == 404:
            if output_json:
                click.echo(
                    json.dumps(
                        {
                            "error": "Backup API not available",
                            "message": "Requires Home Assistant OS or Supervised installation",
                        },
                        indent=2,
                    )
                )
            else:
                click.echo("❌ Backup API not available", err=True)
                click.echo("   Requires Home Assistant OS or Supervised installation.", err=True)
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


@cli.command()
@click.option("--backup-id", required=True, help="Backup ID to delete (get from list-backups.py --json)")
@click.option("--confirm", is_flag=True, help="Confirm destructive operation")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def delete(
    backup_id: str,
    confirm: bool,
    output_json: bool,
) -> None:
    """Delete a backup (requires --confirm)."""
    try:
        if not confirm:
            click.echo("⚠️  This will permanently delete the backup.", err=True)
            click.echo(f"   Backup ID: {backup_id}", err=True)
            click.echo("   Run with --confirm to proceed.", err=True)
            sys.exit(1)

        with httpx.Client(
            base_url=f"{HA_URL}/api",
            headers={
                "Authorization": f"Bearer {HA_TOKEN}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
            timeout=API_TIMEOUT,
        ) as client:
            response = client.delete(f"/backup/remove/{backup_id}")
            response.raise_for_status()

        if output_json:
            click.echo(json.dumps({"deleted": backup_id}, indent=2))
        else:
            click.echo(f"✅ Deleted backup: {backup_id}")

        sys.exit(0)

    except httpx.HTTPStatusError as error:
        if error.response.status_code == 404:
            if output_json:
                click.echo(
                    json.dumps(
                        {
                            "error": "Backup API not available",
                            "message": "Requires Home Assistant OS or Supervised installation",
                        },
                        indent=2,
                    )
                )
            else:
                click.echo("❌ Backup API not available", err=True)
                click.echo("   Requires Home Assistant OS or Supervised installation.", err=True)
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
    cli()
