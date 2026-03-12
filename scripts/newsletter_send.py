#!/usr/bin/env python3
"""
newsletter_send.py — Biweekly newsletter sender via Beehiiv + Apollo distribution.

Runs on the 1st and 15th of each month at 9 AM. Sends broadcast to Beehiiv subscribers
and loads eligible Apollo CRM contacts into the Newsletter Distribution sequence.

Usage:
    python3 scripts/newsletter_send.py [--dry-run]

Environment:
    BEEHIIV_API_KEY — required
    BEEHIIV_PUBLICATION_ID — required (pub_xxx format)
    APOLLO_API_KEY — required
    APOLLO_NEWSLETTER_SEQUENCE_ID — required (create "Newsletter Distribution" sequence in Apollo UI first)
    All found in caseglide-platform/.env.local
"""

import os
import sys
import re
import json
import time
import argparse
import random
from pathlib import Path
from datetime import datetime

import requests
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent
NEWSLETTER_TEMPLATE = PROJECT_ROOT / ".claude" / "templates" / "newsletter-template.md"
NUCLEAR_VERDICTS_FILE = PROJECT_ROOT / "caseglide-platform" / "src" / "data" / "nuclear-verdicts.ts"
ARTICLES_FILE = PROJECT_ROOT / "caseglide-platform" / "src" / "data" / "newsletter-articles.ts"

BEEHIIV_BASE = "https://api.beehiiv.com/v2"
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


def parse_nuclear_verdicts() -> List[Dict]:
    """Parse state verdict data from nuclear-verdicts.ts. Returns states with large verdicts."""
    if not NUCLEAR_VERDICTS_FILE.exists():
        return []
    content = NUCLEAR_VERDICTS_FILE.read_text()
    verdicts = []
    pattern = r'id:\s*"([A-Z]{2})",\s*name:\s*"([^"]+)"[^;]*?largestVerdict:\s*(\d+)'
    for match in re.finditer(pattern, content, re.DOTALL):
        largest = int(match.group(3))
        if largest >= 10:  # Skip states with no significant verdicts
            verdicts.append({"state": match.group(2), "amount": f"${largest}M"})
    return verdicts


def parse_latest_article() -> Optional[Dict]:
    if not ARTICLES_FILE.exists():
        return None
    content = ARTICLES_FILE.read_text()
    slug_match = re.search(r'slug:\s*["\']([^"\']+)["\']', content)
    title_match = re.search(r'title:\s*["\']([^"\']+)["\']', content)
    hook_match = re.search(r'type:\s*["\']paragraph["\'][^}]*?content:\s*["\']([^"\']{20,300})["\']', content, re.DOTALL)
    if not slug_match:
        return None
    slug = slug_match.group(1)
    title = title_match.group(1) if title_match else slug
    hook = hook_match.group(1) if hook_match else title
    return {
        "slug": slug,
        "title": title,
        "hook": hook[:300] if len(hook) > 300 else hook,
        "url": f"https://www.litigationsentinel.com/articles/{slug}"
    }


def render_newsletter(article: dict, verdict: dict):
    """Render newsletter template. Returns (subject, body)."""
    template = NEWSLETTER_TEMPLATE.read_text()

    date_str = datetime.now().strftime("%B %d, %Y").replace(" 0", " ")
    data_point_headline = f"{verdict['amount']} — {verdict['state']}"
    data_point_body = (
        f"Another nuclear verdict logged in our database. {verdict['state']} continues to be "
        f"one of the highest-exposure jurisdictions for large-verdict litigation. "
        f"Is your team tracking exposure in real time?"
    )

    body = template
    body = body.replace("{{date}}", date_str)
    body = body.replace("{{data_point_headline}}", data_point_headline)
    body = body.replace("{{data_point_body}}", data_point_body)
    body = body.replace("{{article_title}}", article["title"])
    body = body.replace("{{article_hook}}", article["hook"])
    body = body.replace("{{article_url}}", article["url"])

    # Extract subject from first line after ---
    subject = f"{data_point_headline} | Litigation Sentinel"

    return subject, body


def send_beehiiv_broadcast(api_key: str, pub_id: str, subject: str, body: str, dry_run: bool) -> Optional[Dict]:
    """Create and send a Beehiiv broadcast."""
    if dry_run:
        print(f"[newsletter_send] DRY RUN: Would send Beehiiv broadcast")
        print(f"  Subject: {subject}")
        print(f"  Body preview: {body[:200]}...")
        return None

    # Create broadcast
    resp = requests.post(
        f"{BEEHIIV_BASE}/publications/{pub_id}/broadcasts",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "subject": subject,
            "content": {"free": body},
            "audience": "all",
            "send_at": "now",
        }
    )
    resp.raise_for_status()
    result = resp.json()
    print(f"[newsletter_send] Beehiiv broadcast sent: {result.get('data', {}).get('id', 'unknown')}")
    return result


def get_apollo_contacts_for_newsletter(api_key: str, sequence_id: str) -> List[str]:
    """Get CRM contacts not already in Newsletter sequence."""
    contact_ids = []
    page = 1
    headers = {"Content-Type": "application/json", "Cache-Control": "no-cache"}

    print(f"[newsletter_send] Fetching Apollo contacts for newsletter distribution...")

    while True:
        resp = requests.post(
            f"{APOLLO_BASE}/contacts/search",
            headers=headers,
            json={
                "api_key": api_key,
                "page": page,
                "per_page": 100,
                "contact_email_status": ["verified"],
            }
        )
        if resp.status_code == 429:
            print("[newsletter_send] Rate limited — waiting 60s")
            time.sleep(60)
            continue
        resp.raise_for_status()
        data = resp.json()

        contacts = data.get("contacts", [])
        if not contacts:
            break

        contact_ids.extend([c["id"] for c in contacts if c.get("id")])

        pagination = data.get("pagination", {})
        if page >= pagination.get("total_pages", 1):
            break
        page += 1
        time.sleep(0.25)

    print(f"[newsletter_send] Found {len(contact_ids)} Apollo contacts for newsletter")
    return contact_ids


def load_contacts_to_sequence(api_key: str, sequence_id: str, contact_ids: List[str], dry_run: bool) -> int:
    """Load contacts into Apollo newsletter sequence in batches of 100."""
    if dry_run:
        print(f"[newsletter_send] DRY RUN: Would load {len(contact_ids)} contacts to sequence {sequence_id}")
        return 0

    loaded = 0
    headers = {"Content-Type": "application/json", "Cache-Control": "no-cache"}
    call_count = 0

    for i in range(0, len(contact_ids), 100):
        batch = contact_ids[i:i + 100]

        resp = requests.post(
            f"{APOLLO_BASE}/emailer_campaigns/{sequence_id}/add_contact_ids",
            headers=headers,
            json={
                "api_key": api_key,
                "contact_ids": batch,
                "send_email_from_email_account_id": None,  # Uses default
                "sequence_active_in_other_campaigns": True,
                "sequence_finished_in_other_campaigns": True,
                "sequence_no_email": False,
            }
        )

        call_count += 1
        if call_count >= 350:
            print("[newsletter_send] Approaching rate limit — sleeping 60s")
            time.sleep(60)
            call_count = 0

        if resp.status_code == 429:
            print("[newsletter_send] Rate limited — sleeping 60s")
            time.sleep(60)
            continue

        if resp.status_code == 200:
            loaded += len(batch)
        else:
            print(f"[newsletter_send] Warning: batch {i//100 + 1} returned {resp.status_code}")

        time.sleep(1.0)

    return loaded


def main():
    parser = argparse.ArgumentParser(description="Biweekly newsletter send via Beehiiv + Apollo")
    parser.add_argument("--dry-run", action="store_true", help="Render content but do not send")
    args = parser.parse_args()

    beehiiv_key = get_env("BEEHIIV_API_KEY")
    pub_id = get_env("BEEHIIV_PUBLICATION_ID")
    apollo_key = get_env("APOLLO_API_KEY")
    newsletter_seq_id = get_env("APOLLO_NEWSLETTER_SEQUENCE_ID")

    if not beehiiv_key or not pub_id:
        print("[newsletter_send] ERROR: BEEHIIV_API_KEY or BEEHIIV_PUBLICATION_ID not set")
        sys.exit(1)
    if not apollo_key:
        print("[newsletter_send] ERROR: APOLLO_API_KEY not set")
        sys.exit(1)
    if not newsletter_seq_id and not args.dry_run:
        print("[newsletter_send] ERROR: APOLLO_NEWSLETTER_SEQUENCE_ID not set.")
        print("  Create 'Newsletter Distribution' sequence in Apollo UI, then add:")
        print("  APOLLO_NEWSLETTER_SEQUENCE_ID=your_sequence_id")
        print("  to caseglide-platform/.env.local")
        sys.exit(1)

    print(f"[newsletter_send] Starting {'DRY RUN' if args.dry_run else 'LIVE RUN'} — {datetime.now().isoformat()}")

    verdicts = parse_nuclear_verdicts()
    article = parse_latest_article()

    if not verdicts:
        print("[newsletter_send] ERROR: No verdicts found in nuclear-verdicts.ts")
        sys.exit(1)
    if not article:
        print("[newsletter_send] ERROR: No articles found in newsletter-articles.ts")
        sys.exit(1)

    verdict = random.choice(verdicts)
    print(f"[newsletter_send] Article: {article['title']}")
    print(f"[newsletter_send] Verdict: {verdict['amount']} — {verdict['state']}")

    subject, body = render_newsletter(article, verdict)
    send_beehiiv_broadcast(beehiiv_key, pub_id, subject, body, args.dry_run)

    # Apollo newsletter distribution
    if newsletter_seq_id:
        contact_ids = get_apollo_contacts_for_newsletter(apollo_key, newsletter_seq_id)
        if contact_ids:
            loaded = load_contacts_to_sequence(apollo_key, newsletter_seq_id, contact_ids, args.dry_run)
            if not args.dry_run:
                print(f"[newsletter_send] Loaded {loaded} contacts to newsletter sequence")
    else:
        print("[newsletter_send] Skipping Apollo distribution — no sequence ID set")

    print(f"[newsletter_send] Complete — {datetime.now().isoformat()}")


if __name__ == "__main__":
    main()
