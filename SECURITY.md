# Security Policy

## Token Security

### Home Assistant Token Scope

The `HOMEASSISTANT_TOKEN` is a **long-lived access token** that grants full API access to your Home Assistant instance.

**Recommendations:**
- Create a dedicated token for Claude Code (not shared with other apps)
- Name it clearly (e.g., "Claude Code")
- Revoke and rotate if compromised
- Never commit tokens to git

### SSH Key Security

For config deployment, SSH access is required.

**Recommendations:**
- Use ed25519 keys (more secure than RSA)
- Use key-based authentication only (disable password auth)
- Don't expose SSH to the internet
- Use a dedicated SSH key for Claude Code if desired

## Environment Variables

All sensitive values are passed via environment variables:

| Variable | Sensitivity | Notes |
|----------|-------------|-------|
| `HOMEASSISTANT_TOKEN` | **HIGH** | Full API access |
| `HA_SSH_HOST` | LOW | Just a hostname/alias |
| `HOMEASSISTANT_URL` | LOW | Network address |

**Never:**
- Commit env vars to git
- Log tokens in scripts
- Share tokens in issues/discussions

## Threat Model

### What these scripts CAN do:
- Control any device in Home Assistant
- Create/modify/delete automations
- Deploy configuration changes
- Trigger backups
- Read all entity states and history

### What these scripts CANNOT do:
- Access your network beyond HA
- Modify system files on HA
- Access other services on your network
- Run arbitrary code on HA (beyond HA's API)

### Protected Files

The deployment scripts **never** overwrite:
- `.storage/` - Device registries, auth tokens
- `secrets.yaml` - Production secrets
- `*.db` - Databases
- `backups/` - Backup files

This is enforced via rsync exclude lists.

## Reporting Vulnerabilities

If you discover a security vulnerability:

1. **Do NOT** open a public issue
2. Email: github@kahl.dev
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

I'll respond within 48 hours and work on a fix.

## Security Updates

Security fixes will be released as soon as possible. Update via Claude Code:

```
/plugin
```

Navigate to **Marketplaces** → `kahl-dev-claude-marketplace` → **Update marketplace**.
