#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
# ]
# ///

"""
Home Assistant Delete Dashboard Script

Delete a Lovelace dashboard via REST API.

Usage:
    uv run delete-dashboard.py my-custom-dashboard --confirm
    uv run delete-dashboard.py --help

Note: Cannot delete the default 'lovelace' dashboard.
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


# Configuration from environment (validated at runtime for --help support)
HA_URL: str = ""
HA_TOKEN: str = ""
API_TIMEOUT = 30.0
USER_AGENT = "HomeAssistant-CLI/1.0"


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


@click.command()
@click.argument("dashboard_id")
@click.option("--confirm", is_flag=True, help="Confirm destructive operation")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def main(
    dashboard_id: str,
    confirm: bool,
    output_json: bool,
) -> None:
    """
    Delete a Lovelace dashboard.

    DASHBOARD_ID is the dashboard URL path (e.g., my-custom-dashboard).

    Note: The default 'lovelace' dashboard cannot be deleted.

    Examples:

        uv run delete-dashboard.py my-dashboard --confirm

        uv run delete-dashboard.py old-dashboard --confirm --json
    """
    _validate_config()
    try:
        # Safety check
        if dashboard_id == "lovelace":
            click.echo("❌ Error: Cannot delete the default 'lovelace' dashboard.", err=True)
            sys.exit(1)

        if not confirm:
            click.echo("⚠️  This will permanently delete the dashboard.", err=True)
            click.echo(f"   Dashboard: {dashboard_id}", err=True)
            click.echo("   Run with --confirm to proceed.", err=True)
            sys.exit(1)

        # Delete from HA
        with httpx.Client(
            base_url=f"{HA_URL}/api",
            headers={
                "Authorization": f"Bearer {HA_TOKEN}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
            timeout=API_TIMEOUT,
        ) as client:
            response = client.delete(f"/lovelace/config/{dashboard_id}")
            response.raise_for_status()

        if output_json:
            click.echo(json.dumps({"deleted": dashboard_id}, indent=2))
        else:
            click.echo(f"✅ Deleted dashboard: {dashboard_id}")

        sys.exit(0)

    except httpx.HTTPStatusError as error:
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
