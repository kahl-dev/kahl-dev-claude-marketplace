# SSH Setup Guide

SSH access is required for config deployment features. This guide covers setup for different Home Assistant installation types.

## Why SSH?

The config deployment workflow needs SSH to:
- Push files to a staging directory
- Copy secrets.yaml for validation
- Deploy validated config to production
- Run `ha core check` for full validation

## Quick Test

First, check if SSH already works:

```bash
ssh your-ha-host "echo 'SSH works!'"
```

If this works, you're done! Just set `HA_SSH_HOST`:

```bash
export HA_SSH_HOST="your-ha-host"
```

## Setup by Installation Type

### Home Assistant OS (Recommended)

HA OS requires the **SSH & Web Terminal** add-on.

1. **Install the add-on:**
   - Settings → Add-ons → Add-on Store
   - Search "SSH & Web Terminal"
   - Install

2. **Configure the add-on:**
   ```yaml
   # In add-on configuration
   authorized_keys:
     - ssh-ed25519 AAAA... your-key
   password: ""  # Disable password auth
   ```

3. **Get your public key:**
   ```bash
   cat ~/.ssh/id_ed25519.pub
   # Or generate if you don't have one:
   ssh-keygen -t ed25519
   ```

4. **Add SSH config:**
   ```bash
   # ~/.ssh/config
   Host ha
     HostName homeassistant.local
     User root
     Port 22222
   ```

5. **Test:**
   ```bash
   ssh ha "echo 'Connected!'"
   ```

### Home Assistant Container (Docker)

For Docker installs, you typically SSH to the host machine.

1. **Ensure SSH is enabled on your Docker host**

2. **Add SSH config:**
   ```bash
   # ~/.ssh/config
   Host ha
     HostName your-docker-host
     User your-username
   ```

3. **Set correct paths:**
   ```bash
   # Docker typically mounts config to a different path
   export HA_CONFIG_PATH="/path/to/ha/config"
   export HA_STAGING_PATH="/path/to/ha/config_staging"
   ```

### Home Assistant Core (venv)

For Core installs, SSH to the machine running HA.

1. **Standard SSH setup to your server**

2. **Set paths based on your installation:**
   ```bash
   export HA_CONFIG_PATH="/home/homeassistant/.homeassistant"
   export HA_STAGING_PATH="/home/homeassistant/.homeassistant_staging"
   ```

## SSH Config Best Practices

Create `~/.ssh/config` with:

```
Host ha
  HostName homeassistant.local
  User root
  Port 22222                    # HA OS uses 22222
  IdentityFile ~/.ssh/id_ed25519
  StrictHostKeyChecking accept-new
  ConnectTimeout 10
```

Then set:

```bash
export HA_SSH_HOST="ha"
```

## Troubleshooting

### "Connection refused" on port 22

HA OS uses port **22222**, not 22:

```bash
ssh -p 22222 root@homeassistant.local
```

### "Permission denied (publickey)"

Your key isn't authorized:

1. Check the add-on configuration includes your public key
2. Restart the SSH add-on
3. Verify key format (should start with `ssh-ed25519` or `ssh-rsa`)

### "Host key verification failed"

The host key changed (common after HA reinstall):

```bash
ssh-keygen -R homeassistant.local
ssh-keygen -R "[homeassistant.local]:22222"
```

### "ha: command not found"

The `ha` CLI isn't available via SSH. This is normal for:
- Container installs
- Core installs
- Some SSH add-on configurations

The scripts handle this gracefully - they skip `ha core check` and rely on API validation.

## Security Considerations

- **Use key-based auth only** - Disable password authentication
- **Use ed25519 keys** - More secure than RSA
- **Restrict SSH access** - Only allow from your local network
- **Don't expose SSH to internet** - Use VPN if needed remotely

See [SECURITY.md](../../../SECURITY.md) for more security guidance.
