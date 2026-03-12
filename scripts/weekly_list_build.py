#!/usr/bin/env python3
"""
weekly_list_build.py — Apollo contact discovery and batch preparation.

Runs every Friday at 10 AM. Finds new contacts matching campaign criteria,
deduplicates against existing Apollo CRM, writes batch to tasks/weekly-list-batch.json,
and requests Wes approval via pending-approvals.md.

Usage:
    python3 scripts/weekly_list_build.py [--dry-run] [--campaign campaign_1_gc_clo]

Environment:
    APOLLO_API_KEY — required (in caseglide-platform/.env.local)
"""

import os
import sys
import json
import time
import argparse
import re
from pathlib import Path
from datetime import datetime

import requests
from typing import Dict, List, Optional
import yaml

# ── Setup ───────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent
CRITERIA_FILE = PROJECT_ROOT / "campaign-criteria.md"
OUTPUT_FILE = PROJECT_ROOT / "tasks" / "weekly-list-batch.json"
APPROVALS_FILE = PROJECT_ROOT / "tasks" / "pending-approvals.md"

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from approval_loop import send_approval_request

APOLLO_BASE = "https://api.apollo.io/v1"

def get_api_key():
    # Try env var first
    key = os.environ.get("APOLLO_API_KEY")
    if key:
        return key
    # Fall back to .env.local
    env_file = PROJECT_ROOT / "caseglide-platform" / ".env.local"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("APOLLO_API_KEY="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("APOLLO_API_KEY not found in env or .env.local")

def load_criteria() -> dict:
    content = CRITERIA_FILE.read_text()
    # Strip markdown — YAML starts after first line starting with a letter (not #)
    yaml_lines = [l for l in content.splitlines() if not l.startswith("#") or l.strip() == ""]
    return yaml.safe_load("\n".join(yaml_lines))


def get_existing_contact_emails(api_key: str) -> set[str]:
    """Pull all existing Apollo CRM contact emails for deduplication."""
    emails = set()
    page = 1
    headers = {"Content-Type": "application/json", "Cache-Control": "no-cache"}

    while True:
        resp = requests.post(
            f"{APOLLO_BASE}/contacts/search",
            headers=headers,
            json={"api_key": api_key, "page": page, "per_page": 100}
        )
        if resp.status_code == 429:
            print("[weekly_list_build] Rate limited on contacts/search — waiting 60s")
            time.sleep(60)
            continue
        resp.raise_for_status()
        data = resp.json()
        contacts = data.get("contacts", [])
        if not contacts:
            break
        for c in contacts:
            email = c.get("email", "")
            if email:
                emails.add(email.lower())

        pagination = data.get("pagination", {})
        if page >= pagination.get("total_pages", 1):
            break
        page += 1
        time.sleep(0.25)

    print(f"[weekly_list_build] Loaded {len(emails)} existing CRM emails for dedup")
    return emails


def search_people(api_key: str, campaign: dict, page: int = 1) -> dict:
    """Search Apollo people database for matching profiles."""
    headers = {"Content-Type": "application/json", "Cache-Control": "no-cache"}
    payload = {
        "api_key": api_key,
        "page": page,
        "per_page": 100,
        "person_titles": campaign["titles"],
        "person_locations": campaign.get("person_locations", ["United States"]),
        "contact_email_status": campaign.get("contact_email_status", ["verified"]),
        "organization_num_employees_ranges": [f"{campaign.get('min_employees', 500)},999999"]
    }
    if campaign.get("industries"):
        payload["organization_industry_tag_ids"] = []  # Would need tag IDs — use keyword search
        payload["q_organization_keyword_tags"] = campaign["industries"]

    resp = requests.post(f"{APOLLO_BASE}/mixed_people/search", headers=headers, json=payload)
    if resp.status_code == 429:
        return None  # Signal rate limit
    resp.raise_for_status()
    return resp.json()


def build_batch(api_key: str, criteria: dict, existing_emails: set[str],
                campaign_key: str, weekly_cap: int, dry_run: bool) -> List[Dict]:
    """Find new contacts for a campaign, deduped and capped."""
    campaign = criteria["campaigns"][campaign_key]
    exclusion_names = {n.lower() for n in criteria.get("global_exclusions", {}).get("names", [])}
    exclusion_emails = {e.lower() for e in criteria.get("global_exclusions", {}).get("emails", [])}

    new_contacts = []
    page = 1

    print(f"\n[weekly_list_build] Searching campaign: {campaign['name']}")

    while len(new_contacts) < weekly_cap:
        if dry_run and page > 2:
            print(f"[weekly_list_build] DRY RUN: stopping at page 2")
            break

        result = search_people(api_key, campaign, page)
        if result is None:
            print("[weekly_list_build] Rate limited — waiting 60s")
            time.sleep(60)
            continue

        people = result.get("people", [])
        if not people:
            break

        for person in people:
            if len(new_contacts) >= weekly_cap:
                break

            email = (person.get("email") or "").lower()
            name = f"{person.get('first_name', '')} {person.get('last_name', '')}".strip().lower()

            # Skip exclusions
            if email in exclusion_emails or email in existing_emails:
                continue
            if any(excl in name for excl in exclusion_names):
                continue
            if not email or person.get("email_status") == "bounced":
                continue

            new_contacts.append({
                "id": person.get("id"),
                "first_name": person.get("first_name"),
                "last_name": person.get("last_name"),
                "email": email,
                "title": person.get("title"),
                "company": person.get("organization", {}).get("name") if person.get("organization") else None,
                "campaign_key": campaign_key,
                "sequence_id": campaign.get("sequence_id"),
                "source": "apollo_people_search",
                "discovered_at": datetime.now().isoformat()
            })

        pagination = result.get("pagination", {})
        if page >= pagination.get("total_pages", 1):
            break
        page += 1
        time.sleep(0.25)

    print(f"[weekly_list_build] Found {len(new_contacts)} new contacts for {campaign_key}")
    return new_contacts


def main():
    parser = argparse.ArgumentParser(description="Weekly Apollo contact list builder")
    parser.add_argument("--dry-run", action="store_true", help="Run without writing batch or requesting approval")
    parser.add_argument("--campaign", help="Run for specific campaign only (e.g. campaign_1_gc_clo)")
    args = parser.parse_args()

    api_key = get_api_key()
    criteria = load_criteria()

    print(f"[weekly_list_build] Starting {'DRY RUN' if args.dry_run else 'LIVE RUN'} — {datetime.now().isoformat()}")

    existing_emails = get_existing_contact_emails(api_key)

    all_batches = []
    summary_items = []

    campaign_keys = [args.campaign] if args.campaign else list(criteria["campaigns"].keys())

    for campaign_key in campaign_keys:
        campaign = criteria["campaigns"][campaign_key]

        if not campaign.get("sequence_id"):
            print(f"[weekly_list_build] SKIP {campaign_key} — no sequence_id set in campaign-criteria.md")
            continue

        weekly_cap = campaign.get("weekly_cap", 500)
        batch = build_batch(api_key, criteria, existing_emails, campaign_key, weekly_cap, args.dry_run)
        all_batches.extend(batch)

        summary_items.append({
            "id": len(summary_items) + 1,
            "description": f"Load {len(batch)} contacts into {campaign['name']} (sequence {campaign['sequence_id']})"
        })

    if not all_batches:
        print("[weekly_list_build] No new contacts found. Nothing to approve.")
        return

    # Write batch file
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    batch_output = {
        "generated_at": datetime.now().isoformat(),
        "dry_run": args.dry_run,
        "total_contacts": len(all_batches),
        "contacts": all_batches
    }

    if not args.dry_run:
        OUTPUT_FILE.write_text(json.dumps(batch_output, indent=2))
        print(f"[weekly_list_build] Wrote {len(all_batches)} contacts to {OUTPUT_FILE}")

        context = (
            f"Weekly list build complete — {datetime.now().strftime('%Y-%m-%d')}. "
            f"Found {len(all_batches)} total new contacts across {len(summary_items)} campaign(s). "
            f"Full batch at tasks/weekly-list-batch.json. Approve to load via apollo_campaign_manager.py."
        )
        send_approval_request(summary_items, "weekly_list_build", context)
    else:
        print(f"\n[DRY RUN] Would write {len(all_batches)} contacts to {OUTPUT_FILE}")
        print(f"[DRY RUN] Would request approval for: {[i['description'] for i in summary_items]}")
        print("[DRY RUN] Batch sample (first 3):")
        for c in all_batches[:3]:
            print(f"  {c['first_name']} {c['last_name']} <{c['email']}> — {c['title']} @ {c['company']}")


if __name__ == "__main__":
    main()
