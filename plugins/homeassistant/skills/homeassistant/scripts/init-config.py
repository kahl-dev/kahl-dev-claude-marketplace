#!/usr/bin/env python3
# /// script
# dependencies = [
#     "click>=8.1.7",
# ]
# ///

"""
Home Assistant Config Bootstrap Script

One-command setup for local HA config repository:
1. Creates directory at specified path
2. Validates SSH connection to HA
3. Initializes git repository
4. Creates .gitignore for HA files
5. Pulls current config from HA (excluding protected files)
6. Creates initial commit
7. Outputs environment variable instructions

Usage:
    uv run init-config.py
    uv run init-config.py --path ~/my-ha-config
    uv run init-config.py --force
    uv run init-config.py --help
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import click


def get_required_env(name: str) -> str:
    """Get required environment variable or fail fast with clear error."""
    value = os.getenv(name)
    if not value:
        click.echo(f"❌ Error: {name} environment variable is required but not set.", err=True)
        click.echo(f'   Set it with: export {name}="<your-value>"', err=True)
        sys.exit(1)
    return value


# Default paths
DEFAULT_LOCAL_PATH = os.path.expanduser("~/ha-config")
HA_CONFIG_PATH = os.getenv("HA_CONFIG_PATH", "/homeassistant")
HA_STAGING_PATH = os.getenv("HA_STAGING_PATH", "/homeassistant/config_staging")

# Files to exclude from rsync (never pull from HA)
RSYNC_EXCLUDES = [
    ".storage/",  # Device registries, entity registry, auth, Zigbee
    "backups/",  # Backup files
    "secrets.yaml",  # Production secrets
    "*.db",  # SQLite databases
    "*.db-shm",  # SQLite WAL files
    "*.db-wal",  # SQLite WAL files
    "home-assistant.log*",  # Log files
    "*.log",  # Other logs
    "tts/",  # Text-to-speech cache
    "deps/",  # Python dependencies
    "__pycache__/",  # Python cache
    ".cloud/",  # Cloud config
    ".ha_run.lock",  # Lock file
    ".HA_VERSION",  # Version file
]

# .gitignore content
GITIGNORE_CONTENT = """# Home Assistant - Files that should NOT be in git

# Secrets (NEVER commit!)
secrets.yaml

# Device state and registries (managed by HA, not config)
.storage/

# Databases
*.db
*.db-shm
*.db-wal

# Logs
*.log
*.log.*
home-assistant.log*

# Backups
backups/

# Cache and generated files
tts/
deps/
__pycache__/
*.pyc

# Cloud config
.cloud/

# Runtime files
.ha_run.lock
.HA_VERSION

# macOS
.DS_Store
"""


def check_ssh_connection(ssh_host: str) -> bool:
    """Check if SSH connection works"""
    try:
        result = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=5", ssh_host, "echo", "ok"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0 and "ok" in result.stdout
    except Exception:
        return False


def check_ha_config_exists(ssh_host: str) -> bool:
    """Check if HA config directory exists"""
    try:
        result = subprocess.run(
            ["ssh", ssh_host, "test", "-d", HA_CONFIG_PATH],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def create_staging_dir(ssh_host: str) -> bool:
    """Create staging directory on HA if it doesn't exist"""
    try:
        result = subprocess.run(
            ["ssh", ssh_host, "mkdir", "-p", HA_STAGING_PATH],
            capture_output=True,
            timeout=30,
        )
        return result.returncode == 0
    except Exception:
        return False


def pull_config(local_path: Path, ssh_host: str) -> tuple[bool, str]:
    """Pull config from HA to local directory"""
    exclude_args = []
    for exclude in RSYNC_EXCLUDES:
        exclude_args.extend(["--exclude", exclude])

    rsync_command = [
        "rsync",
        "-av",
        "--progress",
        *exclude_args,
        f"{ssh_host}:{HA_CONFIG_PATH}/",
        f"{local_path}/",
    ]

    try:
        result = subprocess.run(
            rsync_command,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            return True, result.stdout
        return False, result.stderr
    except subprocess.TimeoutExpired:
        return False, "rsync timed out after 5 minutes"
    except Exception as error:
        return False, str(error)


def init_git_repo(local_path: Path) -> bool:
    """Initialize git repository"""
    try:
        result = subprocess.run(
            ["git", "init"],
            cwd=local_path,
            capture_output=True,
            timeout=30,
        )
        return result.returncode == 0
    except Exception:
        return False


def create_initial_commit(local_path: Path) -> bool:
    """Create initial commit with all files"""
    try:
        subprocess.run(["git", "add", "."], cwd=local_path, capture_output=True, timeout=30)
        result = subprocess.run(
            ["git", "commit", "-m", "🏠 Initial Home Assistant config snapshot"],
            cwd=local_path,
            capture_output=True,
            timeout=30,
        )
        return result.returncode == 0
    except Exception:
        return False


def count_files(local_path: Path) -> int:
    """Count YAML files in directory"""
    return len(list(local_path.glob("**/*.yaml"))) + len(list(local_path.glob("**/*.yml")))


@click.command()
@click.option(
    "--path",
    "-p",
    default=DEFAULT_LOCAL_PATH,
    help=f"Path for local config repository (default: {DEFAULT_LOCAL_PATH})",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing directory (DANGEROUS - will delete existing files)",
)
@click.option(
    "--skip-pull",
    is_flag=True,
    help="Skip pulling config from HA (just create structure)",
)
def main(
    path: str,
    force: bool,
    skip_pull: bool,
) -> None:
    """
    Bootstrap local Home Assistant config repository.

    One-command setup that:
    - Creates local directory
    - Validates SSH connection
    - Pulls current config from HA
    - Initializes git repository
    - Creates .gitignore
    - Makes initial commit

    Examples:

        uv run init-config.py

        uv run init-config.py --path ~/my-ha-config

        uv run init-config.py --force

        uv run init-config.py --skip-pull
    """
    local_path = Path(path).expanduser()

    click.echo("")
    click.echo("=" * 70)
    click.echo("🏠 Home Assistant Config Bootstrap")
    click.echo("=" * 70)
    click.echo("")

    # Step 1: Get required env var
    click.echo("📋 Checking environment...")
    ssh_host = get_required_env("HA_SSH_HOST")
    click.echo(f"   HA_SSH_HOST: {ssh_host}")
    click.echo("")

    # Step 2: Check if directory exists
    if local_path.exists():
        if not force:
            click.echo(f"❌ Directory already exists: {local_path}")
            click.echo("   Use --force to overwrite (DANGEROUS)")
            sys.exit(1)
        else:
            click.echo(f"⚠️  Removing existing directory: {local_path}")
            shutil.rmtree(local_path)

    # Step 3: Check SSH connection
    click.echo("🔐 Checking SSH connection...")
    if not check_ssh_connection(ssh_host):
        click.echo(f"❌ Cannot connect to {ssh_host}")
        click.echo("   Ensure SSH is configured and keys are set up:")
        click.echo(f"   ssh {ssh_host}")
        sys.exit(1)
    click.echo(f"   ✅ Connected to {ssh_host}")
    click.echo("")

    # Step 4: Check HA config exists
    click.echo("📁 Checking HA config directory...")
    if not check_ha_config_exists(ssh_host):
        click.echo(f"❌ HA config not found at {HA_CONFIG_PATH}")
        click.echo("   Check HA_CONFIG_PATH environment variable")
        sys.exit(1)
    click.echo(f"   ✅ Found config at {HA_CONFIG_PATH}")
    click.echo("")

    # Step 5: Create local directory
    click.echo(f"📂 Creating directory: {local_path}")
    local_path.mkdir(parents=True, exist_ok=True)
    click.echo("   ✅ Created")
    click.echo("")

    # Step 6: Create .gitignore
    click.echo("📝 Creating .gitignore...")
    gitignore_path = local_path / ".gitignore"
    gitignore_path.write_text(GITIGNORE_CONTENT)
    click.echo("   ✅ Created")
    click.echo("")

    # Step 7: Pull config from HA
    if not skip_pull:
        click.echo("📥 Pulling config from HA (this may take a while)...")
        success, output = pull_config(local_path, ssh_host)
        if not success:
            click.echo(f"❌ Failed to pull config: {output}")
            sys.exit(1)

        file_count = count_files(local_path)
        click.echo(f"   ✅ Pulled {file_count} YAML files")
        click.echo("")
    else:
        click.echo("⏭️  Skipping config pull (--skip-pull)")
        click.echo("")

    # Step 8: Create staging directory on HA
    click.echo("📁 Creating staging directory on HA...")
    if create_staging_dir(ssh_host):
        click.echo(f"   ✅ Created {HA_STAGING_PATH}")
    else:
        click.echo("   ⚠️  Could not create staging dir (may already exist)")
    click.echo("")

    # Step 9: Initialize git
    click.echo("🔧 Initializing git repository...")
    if not init_git_repo(local_path):
        click.echo("❌ Failed to initialize git")
        sys.exit(1)
    click.echo("   ✅ Initialized")
    click.echo("")

    # Step 10: Create initial commit
    click.echo("💾 Creating initial commit...")
    if create_initial_commit(local_path):
        click.echo("   ✅ Committed")
    else:
        click.echo("   ⚠️  No files to commit or commit failed")
    click.echo("")

    # Success!
    click.echo("=" * 70)
    click.echo("✅ BOOTSTRAP COMPLETE!")
    click.echo("=" * 70)
    click.echo("")
    click.echo(f"📂 Config location: {local_path}")
    click.echo("")
    click.echo("🔧 Add to ~/.zshrc (if not already set):")
    click.echo("")
    click.echo(f'   export HA_LOCAL_CONFIG="{local_path}"')
    click.echo("")
    click.echo("📋 Next steps:")
    click.echo("   1. Edit YAML files in the local directory")
    click.echo("   2. Validate: uv run validate-config.py")
    click.echo("   3. Deploy:   uv run deploy-config.py")
    click.echo("   4. Commit changes with git")
    click.echo("")


if __name__ == "__main__":
    main()
