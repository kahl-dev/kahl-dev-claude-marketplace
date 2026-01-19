#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
# ]
# ///

"""
Home Assistant Trigger Backup Script

Trigger a Home Assistant native backup via API and optionally wait for completion.

Usage:
    uv run trigger-backup.py
    uv run trigger-backup.py --no-wait
    uv run trigger-backup.py --json
    uv run trigger-backup.py --help
"""

import json
import os
import sys
import time
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
API_TIMEOUT = 120.0  # Backups can take a while
USER_AGENT = "HomeAssistant-CLI/1.0"


class HomeAssistantClient:
    """Minimal HTTP client for Home Assistant REST API - backup operations"""

    def __init__(self) -> None:
        self.client = httpx.Client(
            base_url=f"{HA_URL}/api",
            headers={
                "Authorization": f"Bearer {HA_TOKEN}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
            timeout=API_TIMEOUT,
        )

    def __enter__(self) -> "HomeAssistantClient":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        self.client.close()

    def create_backup(self) -> dict[str, Any]:
        """Create a new backup via the backup.create_automatic service"""
        try:
            # Try create_automatic first (HA 2025.x+), fallback to create
            response = self.client.post(
                "/services/backup/create_automatic",
                json={},
            )
            response.raise_for_status()
            return {"status": "initiated", "response": response.json()}
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                # Try legacy create endpoint
                try:
                    response = self.client.post(
                        "/services/backup/create",
                        json={},
                    )
                    response.raise_for_status()
                    return {"status": "initiated", "response": response.json()}
                except httpx.HTTPStatusError as legacy_error:
                    raise Exception(
                        f"API error: {legacy_error.response.status_code} - {legacy_error.response.text}"
                    ) from legacy_error
            raise Exception(f"API error: {error.response.status_code} - {error.response.text}") from error
        except httpx.RequestError as error:
            raise Exception(f"Network error: {error}") from error

    def list_backups(self) -> tuple[list[dict[str, Any]], bool]:
        """
        List all available backups.
        Returns: (backups_list, api_available)
        """
        try:
            response = self.client.get("/backup/info")
            response.raise_for_status()
            data = response.json()
            return data.get("backups", []), True
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                # Backup API not available via REST - return sentinel
                return [], False
            raise Exception(f"API error: {error.response.status_code} - {error.response.text}") from error
        except httpx.RequestError as error:
            raise Exception(f"Network error: {error}") from error

    def get_backup_progress(self) -> dict[str, Any]:
        """Check backup progress/state"""
        try:
            response = self.client.get("/backup/info")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            raise Exception(f"API error: {error.response.status_code} - {error.response.text}") from error
        except httpx.RequestError as error:
            raise Exception(f"Network error: {error}") from error


def format_backup_result(
    backup_id: str | None,
    status: str,
    backup_info: dict[str, Any] | None = None,
) -> str:
    """Format backup result for human-readable output"""
    lines: list[str] = []

    lines.append("")
    lines.append("=" * 80)
    lines.append("💾 Home Assistant Backup")
    lines.append("=" * 80)
    lines.append("")

    status_emoji = "✅" if status == "completed" else "⏳" if status == "in_progress" else "❌"
    lines.append(f"{status_emoji} Status: {status}")

    if backup_id:
        lines.append(f"📋 Backup ID: {backup_id}")

    if backup_info:
        name = backup_info.get("name", "unknown")
        date = backup_info.get("date", "unknown")
        size = backup_info.get("size", 0)
        size_mb = size / (1024 * 1024) if size else 0
        lines.append(f"📁 Name: {name}")
        lines.append(f"📅 Date: {date}")
        lines.append(f"📦 Size: {size_mb:.1f} MB")

    lines.append("")

    return "\n".join(lines)


@click.command()
@click.option(
    "--wait/--no-wait",
    default=True,
    help="Wait for backup to complete (default: wait)",
)
@click.option(
    "--timeout",
    "-t",
    default=300,
    help="Maximum time to wait for backup in seconds (default: 300)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON instead of human-readable format",
)
def main(
    wait: bool,
    timeout: int,
    output_json: bool,
) -> None:
    """
    Trigger a Home Assistant native backup.

    By default, waits for the backup to complete before returning.
    Use --no-wait to trigger and return immediately.

    Examples:

        uv run trigger-backup.py

        uv run trigger-backup.py --no-wait

        uv run trigger-backup.py --timeout 600

        uv run trigger-backup.py --json
    """
    try:
        with HomeAssistantClient() as client:
            # Get list of backups before triggering
            backups_before, api_available = client.list_backups()
            backup_ids_before = {b.get("slug") for b in backups_before}

            # Trigger backup
            client.create_backup()

            if not wait:
                result = {
                    "status": "initiated",
                    "message": "Backup triggered, not waiting for completion",
                }
                if output_json:
                    click.echo(json.dumps(result, indent=2))
                else:
                    click.echo(format_backup_result(None, "initiated"))
                sys.exit(0)

            # Wait for backup to complete
            start_time = time.time()
            new_backup: dict[str, Any] | None = None

            # Check if backup API is available (404 returns False)
            if not api_available:
                # Backup API not available - degrade gracefully
                result = {
                    "status": "initiated",
                    "message": "Backup triggered but cannot verify (API unavailable). Check HA UI.",
                    "api_available": False,
                }
                if output_json:
                    click.echo(json.dumps(result, indent=2))
                else:
                    click.echo("⚠️  Backup triggered but cannot verify completion (backup API unavailable)")
                    click.echo("   Check HA UI or use: ha backup list")
                sys.exit(0)

            while time.time() - start_time < timeout:
                time.sleep(5)  # Poll every 5 seconds

                backups_after, after_api_available = client.list_backups()
                if not after_api_available:
                    # API became unavailable during wait
                    continue

                backup_ids_after = {b.get("slug") for b in backups_after}

                # Find new backup
                new_ids = backup_ids_after - backup_ids_before
                if new_ids:
                    new_slug = new_ids.pop()
                    new_backup = next(
                        (b for b in backups_after if b.get("slug") == new_slug),
                        None,
                    )
                    break

            if new_backup:
                result = {
                    "status": "completed",
                    "backup_id": new_backup.get("slug"),
                    "name": new_backup.get("name"),
                    "date": new_backup.get("date"),
                    "size": new_backup.get("size"),
                }
                if output_json:
                    click.echo(json.dumps(result, indent=2))
                else:
                    click.echo(
                        format_backup_result(
                            new_backup.get("slug"),
                            "completed",
                            new_backup,
                        )
                    )
                sys.exit(0)
            else:
                result = {
                    "status": "timeout",
                    "message": f"Backup did not complete within {timeout} seconds",
                }
                if output_json:
                    click.echo(json.dumps(result, indent=2))
                else:
                    click.echo(f"⚠️  Backup timeout: Did not complete within {timeout}s")
                sys.exit(1)

    except Exception as error:
        error_data = {"error": str(error), "status": "failed"}
        if output_json:
            click.echo(json.dumps(error_data, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
