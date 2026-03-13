#!/usr/bin/env python3
"""
Daily Campaign Digest — CaseGlide GTM Metrics
Pulls Apollo campaign stats + Beehiiv subscriber count.
Outputs a markdown summary to stdout.

Usage:
  python3 daily_campaign_digest.py
  python3 daily_campaign_digest.py --update-revenue    # also append to REVENUE.md
  python3 daily_campaign_digest.py --campaign-id <id>  # use a different campaign

Environment:
  Reads API keys from caseglide-platform/.env.local (auto-detected)
  Or set APOLLO_API_KEY and BEEHIIV_API_KEY env vars directly.
"""

import argparse
import os
import sys
import time
from datetime import datetime, timezone

import requests

try:
    import yaml
except ImportError:
    yaml = None

# --- Paths ---

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
ENV_FILE = os.path.join(PROJECT_ROOT, "caseglide-platform", ".env.local")
REVENUE_FILE = os.path.join(PROJECT_ROOT, "REVENUE.md")

# --- Defaults ---

DEFAULT_CAMPAIGN_ID = "699deee1299e51000d383130"
CAMPAIGN_NAME = "GC/CLO Cold Outreach"

CRITERIA_FILE = os.path.join(PROJECT_ROOT, "campaign-criteria.md")

APOLLO_BASE = "https://api.apollo.io/v1"
BEEHIIV_BASE = "https://api.beehiiv.com/v2"


def load_env(filepath):
    """Parse a .env file into a dict. No dependencies needed."""
    env = {}
    if not os.path.exists(filepath):
        return env
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip()
    return env


def get_key(name, env_overrides):
    """Get API key from environment or .env.local fallback."""
    return os.environ.get(name) or env_overrides.get(name)


def load_active_campaigns():
    """Load all campaigns with sequence_ids set from campaign-criteria.md.

    Returns list of (campaign_key, campaign_dict) in tier_priority order.
    Falls back to DEFAULT_CAMPAIGN_ID if criteria file missing or yaml unavailable.
    """
    if not os.path.exists(CRITERIA_FILE) or yaml is None:
        return [("campaign_1_gc_clo", {"name": CAMPAIGN_NAME, "sequence_id": DEFAULT_CAMPAIGN_ID})]

    content = open(CRITERIA_FILE).read()
    yaml_lines = [l for l in content.splitlines() if not l.startswith("#")]
    try:
        data = yaml.safe_load("\n".join(yaml_lines))
    except Exception:
        return [("campaign_1_gc_clo", {"name": CAMPAIGN_NAME, "sequence_id": DEFAULT_CAMPAIGN_ID})]

    campaigns = data.get("campaigns", {})
    priority = data.get("tier_priority", list(campaigns.keys()))

    active = []
    for key in priority:
        camp = campaigns.get(key, {})
        if camp.get("sequence_id") and camp.get("enabled", True):
            active.append((key, camp))

    # Also include campaign_1_gc_clo if active and not already in priority list
    for key, camp in campaigns.items():
        if key not in [k for k, _ in active] and camp.get("sequence_id") and camp.get("enabled", True):
            active.append((key, camp))

    if not active:
        active = [("campaign_1_gc_clo", {"name": CAMPAIGN_NAME, "sequence_id": DEFAULT_CAMPAIGN_ID})]

    return active


# --- Apollo ---

def fetch_apollo_campaign(api_key, campaign_id):
    """Fetch campaign-level metrics from Apollo."""
    url = f"{APOLLO_BASE}/emailer_campaigns/{campaign_id}"
    headers = {"Content-Type": "application/json", "x-api-key": api_key}
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json().get("emailer_campaign", {})
    except requests.exceptions.HTTPError:
        print(f"ERROR: Apollo returned HTTP {resp.status_code} — {resp.text[:200]}", file=sys.stderr)
        return None
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Apollo network error — {e}", file=sys.stderr)
        return None


def parse_apollo_metrics(campaign):
    """Extract the numbers we care about from Apollo's campaign object."""
    if not campaign:
        return None

    delivered = campaign.get("unique_delivered", 0) or 0
    opened = campaign.get("unique_opened", 0) or 0
    clicked = campaign.get("unique_clicked", 0) or 0
    replied = campaign.get("unique_replied", 0) or 0
    bounced = campaign.get("unique_bounced", 0) or 0
    total_in_sequence = campaign.get("unique_scheduled", 0) or 0

    def rate(num, denom):
        if denom == 0:
            return 0.0
        return round((num / denom) * 100, 1)

    return {
        "name": campaign.get("name", CAMPAIGN_NAME),
        "total_in_sequence": total_in_sequence,
        "delivered": delivered,
        "opened": opened,
        "open_rate": rate(opened, delivered),
        "clicked": clicked,
        "click_rate": rate(clicked, delivered),
        "replied": replied,
        "reply_rate": rate(replied, delivered),
        "bounced": bounced,
        "bounce_rate": rate(bounced, delivered),
        "active": campaign.get("active", False),
    }


# --- Beehiiv ---

def fetch_beehiiv_subscribers(api_key, pub_id):
    """Fetch active subscriber count from Beehiiv (cursor-paginated)."""
    url = f"{BEEHIIV_BASE}/publications/{pub_id}/subscriptions"
    headers = {"Authorization": f"Bearer {api_key}"}
    total = 0
    cursor = None

    try:
        while True:
            params = {"limit": 100, "status": "active"}
            if cursor:
                params["cursor"] = cursor
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            total += len(data.get("data", []))
            if not data.get("has_more", False):
                break
            cursor = data.get("next_cursor")
            if not cursor:
                break
        return {"total": total}
    except requests.exceptions.HTTPError:
        print(f"ERROR: Beehiiv returned HTTP {resp.status_code} — {resp.text[:200]}", file=sys.stderr)
        return None
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Beehiiv network error — {e}", file=sys.stderr)
        return None


# --- Output ---

def build_digest(all_apollo_metrics, beehiiv_data, date_str):
    """Build the markdown digest string for all active campaigns."""
    lines = []
    lines.append(f"# Campaign Digest -- {date_str}")
    lines.append("")

    total_delivered = 0
    total_opened = 0

    for m in all_apollo_metrics:
        if not m:
            continue
        status = "ACTIVE" if m["active"] else "PAUSED"
        lines.append(f"## {m['name']}")
        lines.append(f"- Status: {status}")
        lines.append(f"- Contacts in sequence: {m['total_in_sequence']:,}")
        lines.append(f"- Delivered: {m['delivered']:,}")
        lines.append(f"- Open rate: {m['open_rate']}% ({m['opened']:,}/{m['delivered']:,})")
        if m["clicked"] > 0:
            lines.append(f"- Click rate: {m['click_rate']}% ({m['clicked']:,}/{m['delivered']:,})")
        else:
            lines.append("- Click rate: N/A (tracking disabled)")
        lines.append(f"- Reply rate: {m['reply_rate']}% ({m['replied']:,}/{m['delivered']:,})")
        lines.append(f"- Bounce rate: {m['bounce_rate']}% ({m['bounced']:,}/{m['delivered']:,})")
        lines.append("")
        total_delivered += m["delivered"]
        total_opened += m["opened"]

    if not all_apollo_metrics:
        lines.append("## Apollo Campaigns")
        lines.append("- ERROR: Could not fetch metrics")
        lines.append("")

    # Beehiiv section
    if beehiiv_data:
        lines.append("## Beehiiv Newsletter")
        lines.append(f"- Total subscribers: {beehiiv_data['total']}")
    else:
        lines.append("## Beehiiv Newsletter")
        lines.append("- ERROR: Could not fetch Beehiiv metrics")
    lines.append("")

    # Funnel summary (aggregate)
    subs = beehiiv_data["total"] if beehiiv_data else "?"
    lines.append("## Funnel Summary (All Campaigns)")
    lines.append(f"- Total delivered: {total_delivered:,}")
    lines.append(f"- Total opens: {total_opened:,}")
    lines.append(f"- Newsletter subscribers: {subs}")
    lines.append("- Site visits: check Vercel analytics")
    lines.append("- Briefing submissions: check manually")
    lines.append("")

    return "\n".join(lines)


def append_to_revenue(digest_text):
    """Append digest to REVENUE.md under a dated section."""
    separator = "\n---\n\n"
    with open(REVENUE_FILE, "a") as f:
        f.write(separator)
        f.write(digest_text)
        f.write("\n")
    print(f"Appended digest to {REVENUE_FILE}", file=sys.stderr)


# --- Main ---

def main():
    parser = argparse.ArgumentParser(
        description="Daily Campaign Digest — pull Apollo + Beehiiv metrics"
    )
    parser.add_argument(
        "--campaign-id",
        default=DEFAULT_CAMPAIGN_ID,
        help=f"Apollo campaign/sequence ID (default: {DEFAULT_CAMPAIGN_ID})",
    )
    parser.add_argument(
        "--update-revenue",
        action="store_true",
        help="Append digest to REVENUE.md",
    )
    parser.add_argument(
        "--api-key",
        help="Apollo API key (overrides env/file)",
    )
    args = parser.parse_args()

    # Load keys
    env = load_env(ENV_FILE)
    apollo_key = args.api_key or get_key("APOLLO_API_KEY", env)
    beehiiv_key = get_key("BEEHIIV_API_KEY", env)
    beehiiv_pub = get_key("BEEHIIV_PUBLICATION_ID", env)

    if not apollo_key:
        print("ERROR: No Apollo API key found. Set APOLLO_API_KEY or pass --api-key.", file=sys.stderr)
        sys.exit(1)

    # Fetch data
    date_str = datetime.now().strftime("%Y-%m-%d")

    if args.campaign_id != DEFAULT_CAMPAIGN_ID:
        # Explicit --campaign-id passed: single campaign mode
        campaign_raw = fetch_apollo_campaign(apollo_key, args.campaign_id)
        all_apollo_metrics = [parse_apollo_metrics(campaign_raw)]
    else:
        # Default: report all active campaigns from campaign-criteria.md
        active_campaigns = load_active_campaigns()
        all_apollo_metrics = []
        for camp_key, camp in active_campaigns:
            raw = fetch_apollo_campaign(apollo_key, camp["sequence_id"])
            metrics = parse_apollo_metrics(raw)
            if metrics:
                metrics["name"] = camp.get("name", metrics["name"])
            all_apollo_metrics.append(metrics)
            time.sleep(0.2)

    beehiiv_data = None
    if beehiiv_key and beehiiv_pub:
        beehiiv_data = fetch_beehiiv_subscribers(beehiiv_key, beehiiv_pub)
    else:
        print("WARNING: Beehiiv API key or publication ID not found. Skipping.", file=sys.stderr)

    # Build output
    digest = build_digest(all_apollo_metrics, beehiiv_data, date_str)
    print(digest)

    # Optionally append to REVENUE.md
    if args.update_revenue:
        append_to_revenue(digest)


if __name__ == "__main__":
    main()
