#!/usr/bin/env python3
"""
legacy_list_audit.py — One-time audit of legacy contact lists for Apollo import.

Scans Desktop for CSV/XLSX files with contact data. Filters by target titles.
Deduplicates against Apollo CRM. Writes audit report + import-ready JSON.
Requests approval to import via pending-approvals.md.

Usage:
    python3 scripts/legacy_list_audit.py [--dry-run] [--scan-dir ~/Desktop]

Environment:
    APOLLO_API_KEY — required
    HUBSPOT_PRIVATE_APP_TOKEN — optional (script continues if not set)
"""

import os
import sys
import csv
import json
import time
import argparse
import re
from pathlib import Path
from datetime import datetime

import requests
from typing import Dict, List, Optional
import yaml

PROJECT_ROOT = Path(__file__).parent.parent
AUDIT_REPORT = PROJECT_ROOT / "tasks" / "legacy-list-audit.md"
IMPORT_FILE = PROJECT_ROOT / "tasks" / "legacy-list-import.json"
CRITERIA_FILE = PROJECT_ROOT / "campaign-criteria.md"

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from approval_loop import send_approval_request

APOLLO_BASE = "https://api.apollo.io/v1"


def get_env(key: str) -> Optional[str]:
    val = os.environ.get(key)
    if val:
        return val
    env_file = PROJECT_ROOT / "caseglide-platform" / ".env.local"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip()
    return None


def load_target_titles() -> List[str]:
    content = CRITERIA_FILE.read_text()
    yaml_lines = [l for l in content.splitlines() if not l.startswith("#") or l.strip() == ""]
    criteria = yaml.safe_load("\n".join(yaml_lines))
    return [t.lower() for t in criteria.get("target_titles", [])]


def get_existing_emails(api_key: str) -> set[str]:
    emails = set()
    page = 1
    headers = {"Content-Type": "application/json"}

    while True:
        resp = requests.post(
            f"{APOLLO_BASE}/contacts/search",
            headers=headers,
            json={"api_key": api_key, "page": page, "per_page": 100}
        )
        if resp.status_code == 429:
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

    return emails


def title_matches(title: str, target_titles: List[str]) -> bool:
    if not title:
        return False
    title_lower = title.lower()
    return any(t in title_lower for t in target_titles)


def scan_csv_file(filepath: Path, target_titles: List[str]) -> List[Dict]:
    """Extract matching contacts from a CSV file."""
    contacts = []

    try:
        with open(filepath, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return contacts

            # Detect column names flexibly
            fields = {f.lower().strip(): f for f in reader.fieldnames}
            email_col = next((fields[k] for k in fields if "email" in k), None)
            first_col = next((fields[k] for k in fields if "first" in k), None)
            last_col = next((fields[k] for k in fields if "last" in k), None)
            name_col = next((fields[k] for k in fields if k == "name" or k == "full name"), None)
            title_col = next((fields[k] for k in fields if "title" in k or "position" in k or "role" in k), None)
            company_col = next((fields[k] for k in fields if "company" in k or "organization" in k or "employer" in k), None)

            if not email_col:
                return contacts

            for row in reader:
                email = row.get(email_col, "").strip().lower()
                title = row.get(title_col, "").strip() if title_col else ""

                if not email or "@" not in email:
                    continue
                if title_col and title and not title_matches(title, target_titles):
                    continue

                first = row.get(first_col, "").strip() if first_col else ""
                last = row.get(last_col, "").strip() if last_col else ""
                if not first and not last and name_col:
                    full = row.get(name_col, "").strip()
                    parts = full.split(None, 1)
                    first = parts[0] if parts else ""
                    last = parts[1] if len(parts) > 1 else ""

                contacts.append({
                    "email": email,
                    "first_name": first,
                    "last_name": last,
                    "title": title,
                    "company": row.get(company_col, "").strip() if company_col else "",
                    "source": filepath.name,
                })

    except Exception as e:
        print(f"[legacy_list_audit] Warning: could not parse {filepath.name}: {e}")

    return contacts


def get_hubspot_contacts(token: str, target_titles: List[str]) -> List[Dict]:
    """Fetch contacts from HubSpot (optional)."""
    contacts = []
    after = None
    base = "https://api.hubapi.com/crm/v3/objects/contacts"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        while True:
            params = {
                "limit": 100,
                "properties": "email,firstname,lastname,jobtitle,company",
            }
            if after:
                params["after"] = after

            resp = requests.get(base, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

            for result in data.get("results", []):
                props = result.get("properties", {})
                email = (props.get("email") or "").lower().strip()
                title = props.get("jobtitle", "")

                if not email or "@" not in email:
                    continue
                if title and not title_matches(title, target_titles):
                    continue

                contacts.append({
                    "email": email,
                    "first_name": props.get("firstname", ""),
                    "last_name": props.get("lastname", ""),
                    "title": title,
                    "company": props.get("company", ""),
                    "source": "hubspot",
                })

            paging = data.get("paging", {})
            after = paging.get("next", {}).get("after")
            if not after:
                break

    except Exception as e:
        print(f"[legacy_list_audit] HubSpot error: {e}")

    return contacts


def main():
    parser = argparse.ArgumentParser(description="Legacy contact list audit for Apollo import")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--scan-dir", default=os.path.expanduser("~/Desktop"), help="Directory to scan for CSV files")
    args = parser.parse_args()

    apollo_key = get_env("APOLLO_API_KEY")
    hubspot_token = get_env("HUBSPOT_PRIVATE_APP_TOKEN")
    scan_dir = Path(args.scan_dir)

    if not apollo_key:
        print("[legacy_list_audit] ERROR: APOLLO_API_KEY not set")
        sys.exit(1)

    print(f"[legacy_list_audit] Starting {'DRY RUN' if args.dry_run else 'LIVE RUN'} — {datetime.now().isoformat()}")

    target_titles = load_target_titles()
    print(f"[legacy_list_audit] Target titles: {len(target_titles)}")

    print(f"[legacy_list_audit] Loading existing Apollo CRM emails for dedup...")
    existing_emails = get_existing_emails(apollo_key)
    print(f"[legacy_list_audit] Existing emails in CRM: {len(existing_emails)}")

    all_contacts = []
    sources = {}

    # Scan CSV files
    csv_files = list(scan_dir.glob("**/*.csv")) + list(scan_dir.glob("**/*.CSV"))
    print(f"[legacy_list_audit] Found {len(csv_files)} CSV files in {scan_dir}")

    for csv_file in csv_files:
        batch = scan_csv_file(csv_file, target_titles)
        if batch:
            print(f"  {csv_file.name}: {len(batch)} matching contacts")
            sources[csv_file.name] = len(batch)
            all_contacts.extend(batch)

    # HubSpot (optional)
    if hubspot_token:
        print("[legacy_list_audit] Fetching HubSpot contacts...")
        hs_contacts = get_hubspot_contacts(hubspot_token, target_titles)
        if hs_contacts:
            print(f"  HubSpot: {len(hs_contacts)} matching contacts")
            sources["hubspot"] = len(hs_contacts)
            all_contacts.extend(hs_contacts)
    else:
        print("[legacy_list_audit] HUBSPOT_PRIVATE_APP_TOKEN not set — skipping HubSpot")

    # Dedup against Apollo CRM
    seen_emails = set()
    new_contacts = []
    dupes = 0

    for contact in all_contacts:
        email = contact["email"]
        if email in existing_emails or email in seen_emails:
            dupes += 1
            continue
        seen_emails.add(email)
        new_contacts.append(contact)

    print(f"\n[legacy_list_audit] Results:")
    print(f"  Total found: {len(all_contacts)}")
    print(f"  Duplicates (already in CRM): {dupes}")
    print(f"  Net new for import: {len(new_contacts)}")

    # Group by source
    by_source = {}
    for c in new_contacts:
        src = c["source"]
        by_source.setdefault(src, []).append(c)

    # Write audit report
    report_lines = [
        f"# Legacy List Audit Report\n",
        f"*Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} by legacy_list_audit.py*\n\n",
        f"## Summary\n\n",
        f"- Total contacts found: {len(all_contacts)}\n",
        f"- Already in Apollo CRM: {dupes}\n",
        f"- Net new for import: {len(new_contacts)}\n\n",
        f"## Sources\n\n",
    ]

    for src, contacts in by_source.items():
        report_lines.append(f"### {src} — {len(contacts)} new contacts\n\n")
        for c in contacts[:5]:
            report_lines.append(f"- {c['first_name']} {c['last_name']} <{c['email']}> — {c['title']} @ {c['company']}\n")
        if len(contacts) > 5:
            report_lines.append(f"- *(+{len(contacts) - 5} more)*\n")
        report_lines.append("\n")

    report_lines.append("## Import File\n\n")
    report_lines.append(f"Full import list at: `tasks/legacy-list-import.json`\n")

    if not args.dry_run:
        AUDIT_REPORT.parent.mkdir(parents=True, exist_ok=True)
        AUDIT_REPORT.write_text("".join(report_lines))
        IMPORT_FILE.write_text(json.dumps({
            "generated_at": datetime.now().isoformat(),
            "total": len(new_contacts),
            "contacts": new_contacts
        }, indent=2))
        print(f"[legacy_list_audit] Wrote audit report to {AUDIT_REPORT}")
        print(f"[legacy_list_audit] Wrote import file to {IMPORT_FILE}")

        if new_contacts:
            send_approval_request(
                items=[{"id": 1, "description": f"Import {len(new_contacts)} legacy contacts into Apollo CRM"}],
                task_name="legacy_list_audit",
                context=f"Legacy audit found {len(new_contacts)} net-new contacts not in Apollo CRM. Import file at tasks/legacy-list-import.json. Approve to add to CRM (does not add to any sequence — manual sequence loading required after)."
            )
    else:
        print("\n[DRY RUN] Would write audit report and import file")
        print(f"[DRY RUN] Sample (first 3 new contacts):")
        for c in new_contacts[:3]:
            print(f"  {c['first_name']} {c['last_name']} <{c['email']}> — {c['title']} @ {c['company']}")


if __name__ == "__main__":
    main()
