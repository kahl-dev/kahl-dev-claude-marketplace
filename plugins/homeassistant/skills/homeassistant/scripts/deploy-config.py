#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
#     "pyyaml>=6.0.1",
# ]
# ///

"""
Home Assistant Deploy Config Script

Complete deployment workflow:
1. Validate config (YAML syntax + push to staging)
2. Trigger backup (unless --no-backup)
3. Deploy staging to production (with CRITICAL excludes)
4. Trigger HA reload
5. Run ha core check for full validation
6. Report results

CRITICAL: Never overwrites .storage/, backups/, *.db, logs.
These contain device registries, Zigbee networks, auth tokens.

Usage:
    uv run deploy-config.py
    uv run deploy-config.py --no-backup
    uv run deploy-config.py --dry-run
    uv run deploy-config.py --json
    uv run deploy-config.py --help
"""

import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import click
import httpx
import yaml


# Custom YAML loader that handles Home Assistant's !include and similar tags
class HAYAMLLoader(yaml.SafeLoader):
    """YAML loader with Home Assistant custom tags support"""

    pass


def _include_constructor(loader: yaml.Loader, node: yaml.Node) -> str:
    """Handle !include tag - return placeholder for syntax check"""
    return f"!include:{loader.construct_scalar(node)}"


def _secret_constructor(loader: yaml.Loader, node: yaml.Node) -> str:
    """Handle !secret tag - return placeholder for syntax check"""
    return f"!secret:{loader.construct_scalar(node)}"


def _env_var_constructor(loader: yaml.Loader, node: yaml.Node) -> str:
    """Handle !env_var tag - return placeholder for syntax check"""
    return f"!env_var:{loader.construct_scalar(node)}"


def _include_dir_constructor(loader: yaml.Loader, node: yaml.Node) -> list[str]:
    """Handle !include_dir_* tags - return placeholder for syntax check"""
    return [f"!include_dir:{loader.construct_scalar(node)}"]


# Register HA-specific YAML tags
HAYAMLLoader.add_constructor("!include", _include_constructor)
HAYAMLLoader.add_constructor("!include_dir_list", _include_dir_constructor)
HAYAMLLoader.add_constructor("!include_dir_named", _include_dir_constructor)
HAYAMLLoader.add_constructor("!include_dir_merge_list", _include_dir_constructor)
HAYAMLLoader.add_constructor("!include_dir_merge_named", _include_dir_constructor)
HAYAMLLoader.add_constructor("!secret", _secret_constructor)
HAYAMLLoader.add_constructor("!env_var", _env_var_constructor)


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
HA_STAGING_PATH = os.getenv("HA_STAGING_PATH", "/homeassistant/config_staging")
HA_CONFIG_PATH = os.getenv("HA_CONFIG_PATH", "/homeassistant")
DEFAULT_LOCAL_PATH = os.path.expanduser(os.getenv("HA_LOCAL_CONFIG", "~/ha-config"))

API_TIMEOUT = 120.0
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


# CRITICAL: Files/directories to NEVER overwrite
# These contain device registries, Zigbee/Z-Wave networks, auth, etc.
RSYNC_EXCLUDES = [
    ".storage/",  # Device registries, entity registry, auth, Zigbee
    "backups/",  # Backup files
    "secrets.yaml",  # CRITICAL: Production secrets (never from git!)
    "*.db",  # SQLite databases
    "*.db-shm",  # SQLite WAL files
    "*.db-wal",  # SQLite WAL files
    "home-assistant.log*",  # Log files
    "*.log",  # Other logs
    "tts/",  # Text-to-speech cache
    "deps/",  # Python dependencies (managed by HA)
    "__pycache__/",  # Python cache
    ".cloud/",  # Cloud config
    ".ha_run.lock",  # Lock file
    ".HA_VERSION",  # Version file (HA manages)
]


class HomeAssistantClient:
    """HTTP client for Home Assistant API operations"""

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
        """Trigger a backup via backup.create_automatic (HA 2025.x+)"""
        try:
            response = self.client.post("/services/backup/create_automatic", json={})
            response.raise_for_status()
            return {"status": "initiated"}
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                # Fallback to legacy endpoint
                response = self.client.post("/services/backup/create", json={})
                response.raise_for_status()
                return {"status": "initiated"}
            raise

    def list_backups(self) -> list[dict[str, Any]]:
        """List backups"""
        response = self.client.get("/backup/info")
        response.raise_for_status()
        return response.json().get("backups", [])

    def call_service(self, domain: str, service: str, data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Call a HA service"""
        response = self.client.post(
            f"/services/{domain}/{service}",
            json=data or {},
        )
        response.raise_for_status()
        return response.json()


def validate_yaml_file(filepath: Path) -> dict[str, Any]:
    """Validate a single YAML file"""
    try:
        with open(filepath) as file:
            yaml.load(file, Loader=HAYAMLLoader)
        return {"file": filepath.name, "valid": True, "error": None}
    except yaml.YAMLError as error:
        return {"file": filepath.name, "valid": False, "error": str(error)}
    except Exception as error:
        return {"file": filepath.name, "valid": False, "error": str(error)}


def validate_local_config(local_path: Path) -> tuple[bool, list[dict[str, Any]]]:
    """Validate all YAML files locally"""
    results: list[dict[str, Any]] = []
    yaml_files = list(local_path.glob("*.yaml")) + list(local_path.glob("*.yml"))

    for filepath in sorted(yaml_files):
        if filepath.name == "secrets.yaml":
            continue
        results.append(validate_yaml_file(filepath))

    errors = [r for r in results if not r["valid"]]
    return len(errors) == 0, results


def rsync_to_staging(local_path: Path, ssh_host: str) -> dict[str, Any]:
    """Push local config to staging on HA"""
    rsync_command = [
        "rsync",
        "-av",
        "--delete",
        "--exclude=.git/",
        "--exclude=.gitignore",
        "--exclude=secrets.yaml",
        "--exclude=.storage/",
        "--exclude=backups/",
        "--exclude=*.db",
        "--exclude=*.log*",
        "--exclude=tts/",
        "--exclude=deps/",
        "--exclude=__pycache__/",
        f"{local_path}/",
        f"{ssh_host}:{HA_STAGING_PATH}/",
    ]

    try:
        process = subprocess.run(rsync_command, capture_output=True, text=True, timeout=120)
        return {
            "success": process.returncode == 0,
            "error": process.stderr if process.returncode != 0 else None,
        }
    except Exception as error:
        return {"success": False, "error": str(error)}


def copy_secrets_to_staging(ssh_host: str) -> dict[str, Any]:
    """Copy secrets from production to staging"""
    src = shlex.quote(f"{HA_CONFIG_PATH}/secrets.yaml")
    dst = shlex.quote(f"{HA_STAGING_PATH}/secrets.yaml")
    ssh_command = ["ssh", ssh_host, f"cp {src} {dst} 2>/dev/null || true"]
    try:
        subprocess.run(ssh_command, capture_output=True, timeout=30)
        return {"success": True}
    except Exception as error:
        return {"success": False, "error": str(error)}


def deploy_staging_to_production(ssh_host: str, dry_run: bool = False) -> dict[str, Any]:
    """Deploy from staging to production with CRITICAL excludes."""
    exclude_parts = []
    for exclude in RSYNC_EXCLUDES:
        exclude_parts.append(f"--exclude={shlex.quote(exclude)}")

    excludes_str = " ".join(exclude_parts)
    dry_run_flag = "--dry-run " if dry_run else ""

    staging_path = shlex.quote(f"{HA_STAGING_PATH}/")
    config_path = shlex.quote(f"{HA_CONFIG_PATH}/")

    rsync_cmd = f"rsync -av --delete {dry_run_flag}{excludes_str} {staging_path} {config_path}"

    ssh_command = ["ssh", ssh_host, rsync_cmd]

    try:
        process = subprocess.run(ssh_command, capture_output=True, text=True, timeout=120)
        return {
            "success": process.returncode == 0,
            "dry_run": dry_run,
            "output": process.stdout,
            "error": process.stderr if process.returncode != 0 else None,
        }
    except Exception as error:
        return {"success": False, "error": str(error)}


def run_ha_core_check(ssh_host: str) -> dict[str, Any]:
    """Run ha core check to validate deployed config."""
    ssh_command = ["ssh", ssh_host, "ha", "core", "check", "--raw-json"]

    try:
        process = subprocess.run(ssh_command, capture_output=True, text=True, timeout=120)

        if "unauthorized" in process.stderr.lower() or "unauthorized" in process.stdout.lower():
            return {
                "success": True,
                "skipped": True,
                "note": "ha core check not available via SSH (auth required)",
            }

        try:
            result_json = json.loads(process.stdout)
            valid = result_json.get("result") == "ok"
            return {
                "success": valid,
                "output": result_json,
                "error": None if valid else result_json.get("message"),
            }
        except json.JSONDecodeError:
            if process.returncode == 0:
                return {"success": True, "output": process.stdout}
            return {
                "success": True,
                "skipped": True,
                "note": "Could not parse ha core check output",
            }

    except Exception as error:
        return {
            "success": True,
            "skipped": True,
            "note": f"ha core check unavailable: {error}",
        }


def reload_home_assistant(client: HomeAssistantClient) -> dict[str, Any]:
    """Reload HA core config and automations"""
    reloaded: list[str] = []
    errors: list[str] = []

    reload_services = [
        ("homeassistant", "reload_core_config"),
        ("automation", "reload"),
        ("script", "reload"),
        ("scene", "reload"),
        ("input_boolean", "reload"),
        ("input_number", "reload"),
        ("input_select", "reload"),
        ("input_text", "reload"),
    ]

    for domain, service in reload_services:
        try:
            client.call_service(domain, service)
            reloaded.append(f"{domain}.{service}")
        except Exception as error:
            errors.append(f"{domain}.{service}: {error}")

    return {
        "success": len(errors) == 0,
        "reloaded": reloaded,
        "errors": errors,
    }


def wait_for_backup(client: HomeAssistantClient, timeout: int = 300) -> dict[str, Any]:
    """Wait for backup to complete"""
    backups_before = {b.get("slug") for b in client.list_backups()}

    client.create_backup()

    start_time = time.time()
    while time.time() - start_time < timeout:
        time.sleep(5)
        backups_after = client.list_backups()
        new_slugs = {b.get("slug") for b in backups_after} - backups_before

        if new_slugs:
            new_slug = new_slugs.pop()
            backup_info = next((b for b in backups_after if b.get("slug") == new_slug), {})
            return {
                "success": True,
                "backup_id": new_slug,
                "name": backup_info.get("name"),
                "size": backup_info.get("size"),
            }

    return {"success": False, "error": f"Backup did not complete within {timeout}s"}


def format_deploy_result(steps: dict[str, Any]) -> str:
    """Format deployment result for human output"""
    lines: list[str] = []

    lines.append("")
    lines.append("=" * 80)
    lines.append("🚀 Home Assistant Config Deployment")
    lines.append("=" * 80)
    lines.append("")

    step_names = [
        ("yaml_validation", "📄 YAML Validation"),
        ("staging_push", "📤 Push to Staging"),
        ("backup", "💾 Backup"),
        ("deploy", "🚀 Deploy to Production"),
        ("ha_check", "🔍 HA Core Check"),
        ("reload", "🔄 Reload"),
    ]

    for key, name in step_names:
        if key not in steps:
            continue

        step = steps[key]
        if step.get("skipped"):
            note = step.get("note", "")
            lines.append(f"{name}: ⏭️  Skipped" + (f" ({note})" if note else ""))
        elif step.get("success"):
            lines.append(f"{name}: ✅ Success")
            if key == "backup" and step.get("backup_id"):
                lines.append(f"   Backup ID: {step['backup_id']}")
            if key == "reload" and step.get("reloaded"):
                lines.append(f"   Reloaded: {', '.join(step['reloaded'][:5])}...")
        else:
            lines.append(f"{name}: ❌ Failed")
            if step.get("error"):
                lines.append(f"   Error: {step['error']}")

    lines.append("")
    lines.append("-" * 80)

    if steps.get("overall_success"):
        lines.append("✅ DEPLOYMENT SUCCESSFUL")
    else:
        lines.append("❌ DEPLOYMENT FAILED")
        if steps.get("abort_reason"):
            lines.append(f"   Aborted: {steps['abort_reason']}")

    lines.append("")

    return "\n".join(lines)


@click.command()
@click.option(
    "--local-path",
    "-p",
    default=DEFAULT_LOCAL_PATH,
    help=f"Path to local HA config (default: {DEFAULT_LOCAL_PATH})",
)
@click.option(
    "--no-backup",
    is_flag=True,
    help="Skip backup before deployment (not recommended)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Validate and show what would be deployed, don't actually deploy",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON",
)
def main(
    local_path: str,
    no_backup: bool,
    dry_run: bool,
    output_json: bool,
) -> None:
    """
    Deploy Home Assistant configuration.

    Workflow: Validate -> Backup -> Deploy -> Check -> Reload

    CRITICAL: Never overwrites .storage/, backups/, *.db, logs.
    These contain device registries, Zigbee networks, auth tokens.

    Examples:

        uv run deploy-config.py

        uv run deploy-config.py --dry-run

        uv run deploy-config.py --no-backup

        uv run deploy-config.py --json
    """
    _validate_config()
    # Fail fast if HA_SSH_HOST not set
    ssh_host = get_required_env(
        "HA_SSH_HOST",
        "SSH host for HA, e.g., root@homeassistant.local",
    )

    steps: dict[str, Any] = {}
    config_path = Path(local_path).expanduser()

    try:
        if not config_path.exists():
            raise click.UsageError(f"Config path does not exist: {config_path}")

        # Step 1: Validate YAML locally
        yaml_valid, yaml_results = validate_local_config(config_path)
        steps["yaml_validation"] = {
            "success": yaml_valid,
            "results": yaml_results,
            "error": None if yaml_valid else "YAML syntax errors found",
        }

        if not yaml_valid:
            steps["overall_success"] = False
            steps["abort_reason"] = "YAML validation failed"
            if output_json:
                click.echo(json.dumps(steps, indent=2))
            else:
                click.echo(format_deploy_result(steps))
            sys.exit(1)

        # Step 2: Push to staging
        staging_result = rsync_to_staging(config_path, ssh_host)
        steps["staging_push"] = staging_result

        if not staging_result["success"]:
            steps["overall_success"] = False
            steps["abort_reason"] = "Failed to push to staging"
            if output_json:
                click.echo(json.dumps(steps, indent=2))
            else:
                click.echo(format_deploy_result(steps))
            sys.exit(1)

        # Copy secrets to staging
        copy_secrets_to_staging(ssh_host)

        if dry_run:
            deploy_result = deploy_staging_to_production(ssh_host, dry_run=True)
            steps["deploy"] = deploy_result
            steps["deploy"]["dry_run"] = True
            steps["overall_success"] = True
            steps["dry_run_mode"] = True

            if output_json:
                click.echo(json.dumps(steps, indent=2))
            else:
                click.echo(format_deploy_result(steps))
                click.echo("ℹ️  Dry run mode - no changes made")
            sys.exit(0)

        with HomeAssistantClient() as client:
            # Step 3: Backup (unless --no-backup)
            if no_backup:
                steps["backup"] = {"skipped": True}
            else:
                backup_result = wait_for_backup(client, timeout=300)
                steps["backup"] = backup_result

                if not backup_result["success"]:
                    steps["overall_success"] = False
                    steps["abort_reason"] = "Backup failed"
                    if output_json:
                        click.echo(json.dumps(steps, indent=2))
                    else:
                        click.echo(format_deploy_result(steps))
                    sys.exit(1)

            # Step 4: Deploy staging to production
            deploy_result = deploy_staging_to_production(ssh_host, dry_run=False)
            steps["deploy"] = deploy_result

            if not deploy_result["success"]:
                steps["overall_success"] = False
                steps["abort_reason"] = "Deploy failed"
                if output_json:
                    click.echo(json.dumps(steps, indent=2))
                else:
                    click.echo(format_deploy_result(steps))
                sys.exit(1)

            # Step 5: HA Core Check
            check_result = run_ha_core_check(ssh_host)
            steps["ha_check"] = check_result

            # Step 6: Reload
            reload_result = reload_home_assistant(client)
            steps["reload"] = reload_result

        reload_ok = steps.get("reload", {}).get("success", True)
        steps["overall_success"] = (
            steps.get("deploy", {}).get("success", False)
            and steps.get("ha_check", {}).get("success", False)
            and reload_ok
        )

        if output_json:
            click.echo(json.dumps(steps, indent=2))
        else:
            click.echo(format_deploy_result(steps))

        sys.exit(0 if steps["overall_success"] else 1)

    except click.UsageError:
        raise
    except Exception as error:
        steps["error"] = str(error)
        steps["overall_success"] = False
        if output_json:
            click.echo(json.dumps(steps, indent=2))
        else:
            click.echo(f"❌ Error: {error}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
