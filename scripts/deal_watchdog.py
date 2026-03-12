#!/usr/bin/env python3
"""
deal_watchdog.py — Pipedrive deal staleness monitor + follow-up drafter.

Runs Monday-Friday at 7 AM. Checks all open deals in Pipedrive.
Flags deals with no activity in >3 days. Drafts follow-up emails.
Writes drafts to tasks/deal-followup-drafts.md and requests approval.

Usage:
    python3 scripts/deal_watchdog.py [--dry-run]

Environment:
    PIPEDRIVE_API_TOKEN — required (add to caseglide-platform/.env.local)
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta

import requests
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent
DRAFTS_FILE = PROJECT_ROOT / "tasks" / "deal-followup-drafts.md"
STATUS_FILE = PROJECT_ROOT / "STATUS.md"

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from approval_loop import send_approval_request

PIPEDRIVE_BASE = "https://api.pipedrive.com/v1"
STALE_DAYS = 3

def get_pipedrive_token():
    token = os.environ.get("PIPEDRIVE_API_TOKEN")
    if token:
        return token
    env_file = PROJECT_ROOT / "caseglide-platform" / ".env.local"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("PIPEDRIVE_API_TOKEN="):
                return line.split("=", 1)[1].strip()
    return None


def get_open_deals(token: str) -> List[Dict]:
    """Fetch all open deals from Pipedrive."""
    deals = []
    start = 0

    while True:
        resp = requests.get(
            f"{PIPEDRIVE_BASE}/deals",
            params={"api_token": token, "status": "open", "start": start, "limit": 100}
        )
        resp.raise_for_status()
        data = resp.json()

        if not data.get("success"):
            raise RuntimeError(f"Pipedrive API error: {data.get('error', 'unknown')}")

        batch = data.get("data") or []
        deals.extend(batch)

        pagination = data.get("additional_data", {}).get("pagination", {})
        if not pagination.get("more_items_in_collection"):
            break
        start += 100
        time.sleep(0.1)

    return deals


def get_deal_activities(token: str, deal_id: int) -> List[Dict]:
    """Get recent activities for a deal."""
    resp = requests.get(
        f"{PIPEDRIVE_BASE}/deals/{deal_id}/activities",
        params={"api_token": token, "limit": 5}
    )
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    data = resp.json()
    return data.get("data") or []


def days_since_last_activity(deal: dict, activities: List[Dict]) -> int:
    """Calculate days since last meaningful activity on a deal."""
    dates = []

    # Last activity date from deal object
    if deal.get("last_activity_date"):
        try:
            dates.append(datetime.strptime(deal["last_activity_date"], "%Y-%m-%d"))
        except ValueError:
            pass

    # Update time
    if deal.get("update_time"):
        try:
            dates.append(datetime.strptime(deal["update_time"][:10], "%Y-%m-%d"))
        except ValueError:
            pass

    # Activities
    for act in activities:
        if act.get("due_date"):
            try:
                dates.append(datetime.strptime(act["due_date"], "%Y-%m-%d"))
            except ValueError:
                pass

    if not dates:
        # Fall back to add_time
        if deal.get("add_time"):
            try:
                dates.append(datetime.strptime(deal["add_time"][:10], "%Y-%m-%d"))
            except ValueError:
                pass

    if not dates:
        return 999  # Unknown — treat as very stale

    latest = max(dates)
    return (datetime.now() - latest).days


def draft_followup(deal: dict, days_stale: int) -> str:
    """Draft a follow-up email for a stale deal."""
    deal_name = deal.get("title", "Unknown Deal")
    person_name = deal.get("person_name") or deal.get("person_id", {}).get("name", "")
    org_name = deal.get("org_name") or deal.get("org_id", {}).get("name", "")
    stage = deal.get("stage_id", "")

    # Generic follow-up template — COS or sales-agent should refine before approval
    return f"""**{deal_name}** ({days_stale} days since last touch)
Contact: {person_name} | {org_name}

Subject: Following up — CaseGlide

Hi {person_name.split()[0] if person_name else 'there'},

Following up on our conversation about CaseGlide. Wanted to check in and see
if you have any questions or if there's a good time to reconnect this week.

Best,
Wes

---
*Review draft above. Approve to queue for sending, reject to skip.*
"""


def main():
    parser = argparse.ArgumentParser(description="Deal pipeline staleness watchdog")
    parser.add_argument("--dry-run", action="store_true", help="Run without writing files or requesting approval")
    args = parser.parse_args()

    token = get_pipedrive_token()
    if not token:
        print("[deal_watchdog] ERROR: PIPEDRIVE_API_TOKEN not found.")
        print("[deal_watchdog] Add to caseglide-platform/.env.local:")
        print("  PIPEDRIVE_API_TOKEN=your_token_here")
        print("[deal_watchdog] Get from: caseglide.pipedrive.com → Settings → Personal Preferences → API")
        sys.exit(1)

    print(f"[deal_watchdog] Starting {'DRY RUN' if args.dry_run else 'LIVE RUN'} — {datetime.now().isoformat()}")

    deals = get_open_deals(token)
    print(f"[deal_watchdog] Found {len(deals)} open deals in Pipedrive")

    stale_deals = []

    for deal in deals:
        activities = get_deal_activities(token, deal["id"])
        days = days_since_last_activity(deal, activities)

        if days >= STALE_DAYS:
            stale_deals.append({
                "deal": deal,
                "days_stale": days,
                "draft": draft_followup(deal, days)
            })
            print(f"  FLAG: {deal.get('title')} — {days} days stale")
        else:
            print(f"  OK:   {deal.get('title')} — {days} days")

    if not stale_deals:
        print("[deal_watchdog] No stale deals. All pipelines active.")
        return

    # Write drafts file
    drafts_content = f"# Deal Follow-Up Drafts\n\n*Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} by deal_watchdog.py*\n\n"
    drafts_content += f"**{len(stale_deals)} deals stale (>{STALE_DAYS} days no activity)**\n\n---\n\n"

    for item in stale_deals:
        drafts_content += item["draft"] + "\n---\n\n"

    approval_items = [
        {"id": i + 1, "description": f"Send follow-up for {sd['deal'].get('title')} ({sd['days_stale']} days stale)"}
        for i, sd in enumerate(stale_deals)
    ]

    if not args.dry_run:
        DRAFTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        DRAFTS_FILE.write_text(drafts_content)
        print(f"[deal_watchdog] Wrote {len(stale_deals)} draft(s) to {DRAFTS_FILE}")

        context = (
            f"Deal watchdog found {len(stale_deals)} stale deal(s) — "
            f"{datetime.now().strftime('%Y-%m-%d')}. "
            f"Drafts at tasks/deal-followup-drafts.md. Approve to queue for Wes to send."
        )
        send_approval_request(approval_items, "deal_watchdog", context)
    else:
        print(f"\n[DRY RUN] Would write {len(stale_deals)} drafts to {DRAFTS_FILE}")
        print(f"[DRY RUN] Stale deals: {[sd['deal'].get('title') for sd in stale_deals]}")


if __name__ == "__main__":
    main()
