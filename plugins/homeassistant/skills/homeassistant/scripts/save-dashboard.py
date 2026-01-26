#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
# ]
# ///

"""
Home Assistant Save Dashboard Script

Save or update a Lovelace dashboard configuration via REST API.

Usage:
    uv run save-dashboard.py lovelace --file dashboard.yaml
    uv run save-dashboard.py my-dashboard --file config.json
    uv run save-dashboard.py --help
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


def load_config_file(file_path: str) -> dict[str, Any]:
    """Load dashboard config from JSON or YAML file."""
    with open(file_path) as f:
        content = f.read()

    # Try JSON first
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Try YAML
    try:
        import yaml

        return yaml.safe_load(content)
    except ImportError as e:
        raise Exception("YAML file detected but PyYAML not installed. Use JSON format or install pyyaml.") from e
    except Exception as e:
        raise Exception(f"Failed to parse config file: {e}") from e


@click.command()
@click.argument("dashboard_id", default="lovelace")
@click.option(
    "--file",
    "-f",
    "config_file",
    required=True,
    type=click.Path(exists=True),
    help="Path to dashboard config file (JSON or YAML)",
)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def main(
    dashboard_id: str,
    config_file: str,
    output_json: bool,
) -> None:
    """
    Save a Lovelace dashboard configuration.

    DASHBOARD_ID is the dashboard URL path (default: lovelace).

    Examples:

        uv run save-dashboard.py lovelace --file dashboard.json

        uv run save-dashboard.py my-dashboard --file config.yaml

        uv run save-dashboard.py --file backup.json --json
    """
    try:
        # Load config from file
        config = load_config_file(config_file)

        # Save to HA
        with httpx.Client(
            base_url=f"{HA_URL}/api",
            headers={
                "Authorization": f"Bearer {HA_TOKEN}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
            timeout=API_TIMEOUT,
        ) as client:
            response = client.post(
                f"/lovelace/config/{dashboard_id}",
                json=config,
            )
            response.raise_for_status()

        if output_json:
            click.echo(
                json.dumps(
                    {
                        "saved": True,
                        "dashboard_id": dashboard_id,
                        "config_file": config_file,
                    },
                    indent=2,
                )
            )
        else:
            click.echo(f"✅ Saved dashboard: {dashboard_id}")
            click.echo(f"   From: {config_file}")

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
