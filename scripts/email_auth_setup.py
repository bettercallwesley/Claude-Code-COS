#!/usr/bin/env python3
"""
email_auth_setup.py — One-time Microsoft Graph authentication setup.

Run this once to authenticate with Microsoft and cache the token.
After this, send_email_graph.py works fully autonomously.

Steps this script performs:
1. Check for AZURE_CLIENT_ID and AZURE_TENANT_ID in .env.local
2. If missing, print Azure App Registration instructions
3. Perform device code flow authentication (browser login)
4. Cache the token to .claude/email-token-cache.json

Azure App Registration (one-time, ~5 minutes):
    1. Go to portal.azure.com → Azure Active Directory → App registrations
    2. Click "New registration"
    3. Name: "CaseGlide COS Email Agent"
    4. Supported account types: "Accounts in this organizational directory only"
    5. No redirect URI needed
    6. Click Register
    7. Copy: Application (client) ID → AZURE_CLIENT_ID
    8. Copy: Directory (tenant) ID → AZURE_TENANT_ID
    9. Go to: API permissions → Add a permission → Microsoft Graph
    10. Select: Delegated permissions → search "Mail.Send" → Add
    11. Also add: "Mail.ReadWrite" (for moving sent items)
    12. Click "Grant admin consent" (or sign in as admin)
    13. Go to: Authentication → Add a platform → Mobile and desktop
    14. Check: "https://login.microsoftonline.com/common/oauth2/nativeclient"
    15. Under Advanced settings, enable "Allow public client flows"
    16. Save
    17. Add AZURE_CLIENT_ID and AZURE_TENANT_ID to caseglide-platform/.env.local

Usage:
    python3 scripts/email_auth_setup.py

Dependencies:
    pip3 install msal requests pyyaml
"""

import os
import sys
from pathlib import Path

try:
    import msal
except ImportError:
    print("ERROR: msal not installed.")
    print("Run: pip3 install msal requests pyyaml")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / "caseglide-platform" / ".env.local"
TOKEN_CACHE_FILE = PROJECT_ROOT / ".claude" / "email-token-cache.json"

SCOPES = ["Mail.Send", "Mail.ReadWrite"]


def load_env() -> dict:
    env = {}
    if not ENV_FILE.exists():
        return env
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def main():
    print("=== CaseGlide Email Auth Setup ===\n")

    env = load_env()
    client_id = os.environ.get("AZURE_CLIENT_ID") or env.get("AZURE_CLIENT_ID")
    tenant_id = os.environ.get("AZURE_TENANT_ID") or env.get("AZURE_TENANT_ID")

    if not client_id or not tenant_id:
        print("AZURE_CLIENT_ID and/or AZURE_TENANT_ID not found in .env.local\n")
        print("Complete the Azure App Registration first:")
        print("-" * 60)
        print("1. Go to: portal.azure.com → Azure Active Directory → App registrations")
        print("2. New registration → Name: 'CaseGlide COS Email Agent'")
        print("3. Account type: 'Accounts in this organizational directory only'")
        print("4. Register (no redirect URI needed)")
        print("5. Copy Application (client) ID → AZURE_CLIENT_ID")
        print("6. Copy Directory (tenant) ID → AZURE_TENANT_ID")
        print("7. API permissions → Add → Microsoft Graph → Delegated:")
        print("   - Mail.Send")
        print("   - Mail.ReadWrite")
        print("8. Grant admin consent")
        print("9. Authentication → Add platform → Mobile/desktop apps")
        print("   Enable: 'Allow public client flows'")
        print("10. Add to caseglide-platform/.env.local:")
        print("    AZURE_CLIENT_ID=<your-client-id>")
        print("    AZURE_TENANT_ID=<your-tenant-id>")
        print("-" * 60)
        print("\nThen re-run this script.")
        return

    print(f"Found AZURE_CLIENT_ID: {client_id[:8]}...")
    print(f"Found AZURE_TENANT_ID: {tenant_id[:8]}...")

    cache = msal.SerializableTokenCache()
    if TOKEN_CACHE_FILE.exists():
        cache.deserialize(TOKEN_CACHE_FILE.read_text())
        print(f"\nExisting token cache found at {TOKEN_CACHE_FILE}")

    app = msal.PublicClientApplication(
        client_id=client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        token_cache=cache,
    )

    # Check if we already have a valid token
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            print(f"\nExisting token valid for: {accounts[0]['username']}")
            print("Auth already configured — send_email_graph.py is ready to use.")
            TOKEN_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            TOKEN_CACHE_FILE.write_text(cache.serialize())
            return

    # Device code flow
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        print(f"ERROR: {flow.get('error_description', 'Unknown error')}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print(flow["message"])
    print("=" * 60)
    print("\nWaiting for authentication...")

    result = app.acquire_token_by_device_flow(flow)

    if "access_token" in result:
        TOKEN_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_CACHE_FILE.write_text(cache.serialize())
        print(f"\nAuthentication successful!")
        print(f"Token cached to: {TOKEN_CACHE_FILE}")
        print("\nsend_email_graph.py is now ready for autonomous email sending.")
    else:
        print(f"\nERROR: {result.get('error_description', result.get('error', 'Unknown'))}")
        sys.exit(1)


if __name__ == "__main__":
    main()
