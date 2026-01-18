#!/usr/bin/env python3
# /// script
# dependencies = ["httpx", "click"]
# ///

import os
import sys
import httpx
import json
import click

def get_ha_url():
    return os.getenv("HOMEASSISTANT_URL", "http://homeassistant.local:8123")

def get_ha_token():
    token = os.getenv("HOMEASSISTANT_TOKEN")
    if not token:
        raise EnvironmentError("Missing HOMEASSISTANT_TOKEN environment variable")
    return token

@click.command()
@click.argument('automation_config', type=str)
def create_automation(automation_config):
    """Create a Home Assistant automation via REST API."""
    url = get_ha_url()
    token = get_ha_token()
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Parse automation config
    config = json.loads(automation_config)
    
    # Try POST to config endpoint
    endpoint = f"{url}/api/config/automation/config/{config.get('id', 'new')}"
    
    print(f"🔧 Creating automation: {config.get('alias', 'Unknown')}")
    print(f"📍 Endpoint: {endpoint}")
    
    try:
        response = httpx.post(endpoint, headers=headers, json=config, timeout=10)
        response.raise_for_status()
        print(f"✅ Automation created successfully!")
        print(json.dumps(response.json(), indent=2))
    except httpx.HTTPError as e:
        print(f"❌ Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        sys.exit(1)

if __name__ == "__main__":
    create_automation()
