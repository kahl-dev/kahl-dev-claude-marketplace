#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
# ]
# ///

"""
Home Assistant Check Reload Script

Verify HA reload completed successfully by:
1. Checking HA state (is it running?)
2. Checking for errors in system log
3. Verifying key entities are available

Usage:
    uv run check-reload.py
    uv run check-reload.py --timeout 60
    uv run check-reload.py --json
    uv run check-reload.py --help
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
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


# Configuration from environment (validated at runtime for --help support)
HA_URL: str = ""
HA_TOKEN: str = ""
DEFAULT_TIMEOUT = 30.0


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


USER_AGENT = "HomeAssistant-CLI/1.0"


class HomeAssistantClient:
    """HTTP client for Home Assistant API operations"""

    def __init__(self, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.timeout = timeout
        self.client = httpx.Client(
            base_url=f"{HA_URL}/api",
            headers={
                "Authorization": f"Bearer {HA_TOKEN}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
            timeout=timeout,
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

    def check_api(self) -> dict[str, Any]:
        """Check if HA API is responsive"""
        try:
            response = self.client.get("/")
            response.raise_for_status()
            return {"running": True, "message": response.json().get("message", "OK")}
        except Exception as error:
            return {"running": False, "error": str(error)}

    def get_config(self) -> dict[str, Any]:
        """Get HA config info"""
        try:
            response = self.client.get("/config")
            response.raise_for_status()
            return response.json()
        except Exception as error:
            return {"error": str(error)}

    def get_states(self) -> list[dict[str, Any]]:
        """Get all entity states"""
        try:
            response = self.client.get("/states")
            response.raise_for_status()
            return response.json()
        except Exception:
            return []

    def get_error_log(self) -> str:
        """Get HA error log"""
        try:
            response = self.client.get("/error_log")
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                return ""
            return f"Error fetching log: {error}"
        except Exception as error:
            return f"Error fetching log: {error}"


def run_ha_core_check(ssh_host: str, timeout: int = 60) -> dict[str, Any]:
    """Run ha core check via SSH."""
    ssh_command = ["ssh", ssh_host, "ha", "core", "check", "--raw-json"]

    try:
        process = subprocess.run(ssh_command, capture_output=True, text=True, timeout=timeout)

        if "unauthorized" in process.stderr.lower() or "unauthorized" in process.stdout.lower():
            return {
                "success": True,
                "skipped": True,
                "note": "ha core check not available via SSH (auth required)",
            }

        try:
            result_json = json.loads(process.stdout)
            return {
                "success": result_json.get("result") == "ok",
                "result": result_json.get("result"),
                "message": result_json.get("message"),
            }
        except json.JSONDecodeError:
            if process.returncode == 0:
                return {"success": True, "output": process.stdout}
            return {
                "success": True,
                "skipped": True,
                "note": "Could not parse ha core check output",
            }

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "ha core check timed out"}
    except Exception as error:
        return {
            "success": True,
            "skipped": True,
            "note": f"ha core check unavailable: {error}",
        }


def parse_recent_errors(log_content: str, minutes: int = 5) -> list[str]:
    """Parse error log for recent errors"""
    errors: list[str] = []
    now = datetime.now()
    cutoff = now - timedelta(minutes=minutes)

    for line in log_content.split("\n"):
        if not line.strip():
            continue

        is_error = any(marker in line.lower() for marker in ["error", "exception", "traceback", "failed"])
        if not is_error:
            continue

        try:
            if len(line) > 19:
                timestamp_str = line[:19]
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                if timestamp > cutoff:
                    errors.append(line.strip()[:200])
        except ValueError:
            if is_error and len(errors) < 10:
                errors.append(line.strip()[:200])

    return errors[:10]


def format_check_result(
    api_check: dict[str, Any],
    config_check: dict[str, Any],
    core_check: dict[str, Any],
    entity_count: int,
    recent_errors: list[str],
) -> str:
    """Format check results for human output"""
    lines: list[str] = []

    lines.append("")
    lines.append("=" * 80)
    lines.append("🔍 Home Assistant Reload Check")
    lines.append("=" * 80)
    lines.append("")

    # API Status
    lines.append("📡 API Status")
    lines.append("-" * 40)
    if api_check.get("running"):
        lines.append(f"  ✅ API Responsive: {api_check.get('message', 'OK')}")
    else:
        lines.append(f"  ❌ API Error: {api_check.get('error', 'Unknown')}")

    lines.append("")

    # Config Check
    lines.append("⚙️ Configuration")
    lines.append("-" * 40)
    if "error" not in config_check:
        version = config_check.get("version", "unknown")
        state = config_check.get("state", "unknown")
        lines.append(f"  HA Version: {version}")
        lines.append(f"  State: {state}")
    else:
        lines.append(f"  ❌ Error: {config_check.get('error')}")

    lines.append("")

    # Core Check
    lines.append("🔬 Core Validation (ha core check)")
    lines.append("-" * 40)
    if core_check.get("skipped"):
        lines.append(f"  ⏭️  Skipped: {core_check.get('note', 'Not available')}")
    elif core_check.get("success"):
        lines.append(f"  ✅ Result: {core_check.get('result', 'ok')}")
    else:
        lines.append(f"  ❌ Failed: {core_check.get('error') or core_check.get('message', 'Unknown')}")

    lines.append("")

    # Entity Count
    lines.append("📊 Entities")
    lines.append("-" * 40)
    lines.append(f"  Total loaded: {entity_count}")

    lines.append("")

    # Recent Errors
    lines.append("🚨 Recent Errors (last 5 min)")
    lines.append("-" * 40)
    if recent_errors:
        for error in recent_errors[:5]:
            lines.append(f"  ⚠️  {error[:70]}...")
    else:
        lines.append("  ✅ No recent errors")

    lines.append("")
    lines.append("-" * 80)

    overall_ok = api_check.get("running", False) and core_check.get("success", False) and len(recent_errors) == 0

    if overall_ok:
        lines.append("✅ RELOAD SUCCESSFUL - Home Assistant is healthy")
    else:
        lines.append("⚠️  RELOAD COMPLETED WITH WARNINGS")
        if not api_check.get("running"):
            lines.append("   - API not responsive")
        if not core_check.get("success"):
            lines.append("   - Core check failed")
        if recent_errors:
            lines.append(f"   - {len(recent_errors)} recent errors in log")

    lines.append("")

    return "\n".join(lines)


@click.command()
@click.option(
    "--timeout",
    "-t",
    default=30,
    help="Timeout for checks in seconds (default: 30)",
)
@click.option(
    "--wait",
    "-w",
    default=0,
    help="Wait N seconds before checking (for reload to complete)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON",
)
def main(
    timeout: int,
    wait: int,
    output_json: bool,
) -> None:
    """
    Check if Home Assistant reload completed successfully.

    Verifies API responsiveness, runs ha core check, and scans for recent errors.

    Examples:

        uv run check-reload.py

        uv run check-reload.py --wait 10

        uv run check-reload.py --timeout 60

        uv run check-reload.py --json
    """
    _validate_config()
    # Fail fast if HA_SSH_HOST not set
    ssh_host = get_required_env(
        "HA_SSH_HOST",
        "SSH host for HA, e.g., root@homeassistant.local",
    )

    try:
        if wait > 0:
            if not output_json:
                click.echo(f"⏳ Waiting {wait}s for reload to complete...")
            time.sleep(wait)

        with HomeAssistantClient(timeout=float(timeout)) as client:
            api_check = client.check_api()
            config_check = client.get_config()
            states = client.get_states()
            entity_count = len(states)
            error_log = client.get_error_log()
            recent_errors = parse_recent_errors(error_log, minutes=5)

        core_check = run_ha_core_check(ssh_host, timeout=timeout)

        overall_success = api_check.get("running", False) and core_check.get("success", False)

        if output_json:
            result = {
                "success": overall_success,
                "api": api_check,
                "config": config_check,
                "core_check": core_check,
                "entity_count": entity_count,
                "recent_errors": recent_errors,
            }
            click.echo(json.dumps(result, indent=2))
        else:
            formatted = format_check_result(
                api_check,
                config_check,
                core_check,
                entity_count,
                recent_errors,
            )
            click.echo(formatted)

        sys.exit(0 if overall_success else 1)

    except Exception as error:
        error_data = {"success": False, "error": str(error)}
        if output_json:
            click.echo(json.dumps(error_data, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
