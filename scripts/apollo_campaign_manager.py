#!/usr/bin/env python3
"""
Apollo Campaign Manager — Bulk Operations Script
Created: March 2, 2026 (CCO Post-Mortem)

Handles:
- Searching contacts with filters
- Adding contacts to sequences with correct flags
- Rate limit management with exponential backoff
- Progress logging

Usage:
  python3 apollo_campaign_manager.py add-contacts
  python3 apollo_campaign_manager.py count-contacts
  python3 apollo_campaign_manager.py count-people

Environment:
  APOLLO_API_KEY must be set (or pass --api-key)
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

import requests as _requests


# --- Configuration ---

BASE_URL = "https://api.apollo.io/v1"

DEFAULT_SEQUENCE_ID = "699deee1299e51000d383130"
DEFAULT_MAILBOX_ID = "69a598bdfd80760021e01e93"

DEFAULT_PERSON_TITLES = [
    "General Counsel",
    "Chief Legal Officer",
    "Deputy General Counsel",
    "VP Legal",
    "Vice President Legal",
    "VP of Legal",
    "Vice President of Legal",
    "VP of Litigation",
    "Vice President of Litigation",
    "VP Legal Operations",
    "Vice President Legal Operations",
    "Director of Legal Operations",
    "Chief Risk Officer",
    "VP Risk",
    "Vice President Risk",
    "VP of Risk Management",
    "Vice President of Risk Management",
    "VP of Risk",
    "Vice President of Risk",
    "VP Claims",
    "Vice President of Claims",
    "Chief Claims Officer",
    "Chief Information Officer",
    "Vice President of Information Technology",
]

DEFAULT_PERSON_LOCATIONS = ["United States"]

CONTACTS_PER_BATCH = 100
SEARCH_SLEEP = 0.25
ADD_BATCH_SLEEP = 1.0
RATE_LIMIT_INITIAL_BACKOFF = 60
RATE_LIMIT_MAX_RETRIES = 5
HOURLY_CALL_LIMIT = 350  # Apollo allows ~400 API calls/hr on add_contact_ids


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def api_request(endpoint, data, api_key, method="POST"):
    url = f"{BASE_URL}/{endpoint}"
    headers = {"Content-Type": "application/json", "x-api-key": api_key}

    retries = 0
    backoff = RATE_LIMIT_INITIAL_BACKOFF

    while retries <= RATE_LIMIT_MAX_RETRIES:
        try:
            resp = _requests.request(method, url, json=data, headers=headers, timeout=30)
            if resp.status_code == 429:
                retries += 1
                if retries > RATE_LIMIT_MAX_RETRIES:
                    log(f"ERROR: Rate limit exceeded after {RATE_LIMIT_MAX_RETRIES} retries.")
                    raise Exception("Rate limit exceeded")
                log(f"Rate limited (429). Waiting {backoff}s before retry {retries}/{RATE_LIMIT_MAX_RETRIES}...")
                time.sleep(backoff)
                backoff *= 2
                continue
            resp.raise_for_status()
            return resp.json()
        except _requests.exceptions.HTTPError as e:
            log(f"ERROR: HTTP {resp.status_code} — {resp.text[:200]}")
            raise
        except _requests.exceptions.RequestException as e:
            log(f"ERROR: Network error — {e}")
            raise

    return None


def search_contacts(api_key, page=1, per_page=100, titles=None, locations=None):
    data = {
        "page": page,
        "per_page": per_page,
        "sort_by_field": "contact_last_activity_date",
        "sort_ascending": False,
        "person_titles": titles or DEFAULT_PERSON_TITLES,
        "person_locations": locations or DEFAULT_PERSON_LOCATIONS,
        "contact_email_status": ["verified"],
    }
    return api_request("contacts/search", data, api_key)


def search_people(api_key, page=1, per_page=100, titles=None, locations=None):
    data = {
        "page": page,
        "per_page": per_page,
        "person_titles": titles or DEFAULT_PERSON_TITLES,
        "person_locations": locations or DEFAULT_PERSON_LOCATIONS,
        "prospected_by_current_team": ["no"],
    }
    return api_request("mixed_people/search", data, api_key)


def add_contacts_to_sequence(api_key, contact_ids, sequence_id, mailbox_id):
    """
    CRITICAL: sequence_active_in_other_campaigns and
    sequence_finished_in_other_campaigns MUST be True.
    Defaults are False, which silently excludes most contacts.
    """
    data = {
        "contact_ids": contact_ids,
        "emailer_campaign_id": sequence_id,
        "send_email_from_email_account_id": mailbox_id,
        "sequence_active_in_other_campaigns": True,
        "sequence_finished_in_other_campaigns": True,
        "sequence_no_email": False,
    }
    endpoint = f"emailer_campaigns/{sequence_id}/add_contact_ids"
    return api_request(endpoint, data, api_key)


def get_all_contact_ids(api_key, titles=None, locations=None):
    all_ids = []
    result = search_contacts(api_key, page=1, per_page=100, titles=titles, locations=locations)
    if not result:
        return []

    total = result.get("pagination", {}).get("total_entries", 0)
    total_pages = result.get("pagination", {}).get("total_pages", 0)
    log(f"Found {total} contacts across {total_pages} pages")

    for contact in result.get("contacts", []):
        if contact.get("id"):
            all_ids.append(contact["id"])

    log(f"Page 1/{total_pages}: {len(all_ids)} IDs collected")

    for page in range(2, total_pages + 1):
        time.sleep(SEARCH_SLEEP)
        result = search_contacts(api_key, page=page, per_page=100, titles=titles, locations=locations)
        if not result:
            log(f"WARNING: Page {page} returned None. Stopping.")
            break

        page_ids = [c["id"] for c in result.get("contacts", []) if c.get("id")]
        all_ids.extend(page_ids)
        log(f"Page {page}/{total_pages}: {len(page_ids)} IDs (total: {len(all_ids)})")

    log(f"Total contact IDs collected: {len(all_ids)}")
    return all_ids


def bulk_add_to_sequence(api_key, contact_ids, sequence_id, mailbox_id):
    total = len(contact_ids)
    added = 0
    skipped = 0
    errors = 0
    hourly_calls = 0
    hour_start = time.time()

    log(f"Starting bulk add: {total} contacts -> sequence {sequence_id}")
    log(f"Rate limit strategy: {CONTACTS_PER_BATCH}/batch, {HOURLY_CALL_LIMIT} API calls/hour max")

    for i in range(0, total, CONTACTS_PER_BATCH):
        batch = contact_ids[i:i + CONTACTS_PER_BATCH]
        batch_num = (i // CONTACTS_PER_BATCH) + 1
        total_batches = (total + CONTACTS_PER_BATCH - 1) // CONTACTS_PER_BATCH

        elapsed = time.time() - hour_start
        if elapsed >= 3600:
            hourly_calls = 0
            hour_start = time.time()
            log("Hourly call counter reset")

        if hourly_calls >= HOURLY_CALL_LIMIT:
            wait_time = 3600 - elapsed + 10
            if wait_time > 0:
                log(f"Hourly call limit reached ({hourly_calls}/{HOURLY_CALL_LIMIT}). "
                    f"Waiting {wait_time:.0f}s for reset...")
                time.sleep(wait_time)
                hourly_calls = 0
                hour_start = time.time()

        log(f"Batch {batch_num}/{total_batches}: Adding {len(batch)} contacts...")

        try:
            result = add_contacts_to_sequence(api_key, batch, sequence_id, mailbox_id)
            hourly_calls += 1
            if result:
                batch_added = len(result.get("contacts", []))
                batch_skipped = len(batch) - batch_added
                added += batch_added
                skipped += batch_skipped
                log(f"  Added: {batch_added}, Skipped: {batch_skipped} | Total: {added}/{total} (call {hourly_calls}/{HOURLY_CALL_LIMIT})")
            else:
                errors += len(batch)
                log(f"  ERROR: Null response for batch {batch_num}")
        except Exception as e:
            errors += len(batch)
            hourly_calls += 1
            log(f"  ERROR: {e}")

        if i + CONTACTS_PER_BATCH < total:
            time.sleep(ADD_BATCH_SLEEP)

    log("=" * 60)
    log(f"COMPLETE: {added} added, {skipped} skipped, {errors} errors of {total}")
    log("=" * 60)

    return {"added": added, "skipped": skipped, "errors": errors, "total": total}


def cmd_count_contacts(args):
    api_key = args.api_key or os.environ.get("APOLLO_API_KEY")
    if not api_key:
        log("ERROR: No API key. Set APOLLO_API_KEY or pass --api-key")
        sys.exit(1)
    result = search_contacts(api_key, page=1, per_page=1)
    total = result.get("pagination", {}).get("total_entries", 0)
    log(f"CRM contacts matching filters: {total}")


def cmd_count_people(args):
    api_key = args.api_key or os.environ.get("APOLLO_API_KEY")
    if not api_key:
        log("ERROR: No API key. Set APOLLO_API_KEY or pass --api-key")
        sys.exit(1)
    result = search_people(api_key, page=1, per_page=1)
    total = result.get("pagination", {}).get("total_entries", 0)
    log(f"People (non-contacts) matching filters: {total}")


def cmd_add_contacts(args):
    api_key = args.api_key or os.environ.get("APOLLO_API_KEY")
    if not api_key:
        log("ERROR: No API key. Set APOLLO_API_KEY or pass --api-key")
        sys.exit(1)

    sequence_id = args.sequence_id
    mailbox_id = args.mailbox_id

    log(f"Sequence: {sequence_id}")
    log(f"Mailbox: {mailbox_id}")

    log("Phase 1: Collecting contact IDs...")
    contact_ids = get_all_contact_ids(api_key)
    if not contact_ids:
        log("No contacts found.")
        sys.exit(1)

    log(f"Phase 2: Adding {len(contact_ids)} contacts to sequence...")
    bulk_add_to_sequence(api_key, contact_ids, sequence_id, mailbox_id)


def main():
    parser = argparse.ArgumentParser(description="Apollo Campaign Manager")
    parser.add_argument("--api-key", help="Apollo API key (or set APOLLO_API_KEY)")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("count-contacts", help="Count CRM contacts matching filters")
    subparsers.add_parser("count-people", help="Count non-contact people matching filters")

    sub_add = subparsers.add_parser("add-contacts", help="Add all matching contacts to sequence")
    sub_add.add_argument("--sequence-id", default=DEFAULT_SEQUENCE_ID)
    sub_add.add_argument("--mailbox-id", default=DEFAULT_MAILBOX_ID)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "count-contacts":
        cmd_count_contacts(args)
    elif args.command == "count-people":
        cmd_count_people(args)
    elif args.command == "add-contacts":
        cmd_add_contacts(args)


if __name__ == "__main__":
    main()
