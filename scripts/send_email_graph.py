#!/usr/bin/env python3
"""
send_email_graph.py — Autonomous email sender via Microsoft Graph API.

Sends emails as wesley@caseglide.com through Outlook. Reads structured
draft files from tasks/pending-emails/ or accepts direct arguments.

Usage:
    python3 scripts/send_email_graph.py --draft tasks/pending-emails/pavarini.md
    python3 scripts/send_email_graph.py --to email@co.com --subject "Subject" --body "Body"
    python3 scripts/send_email_graph.py --list  # show pending drafts
    python3 scripts/send_email_graph.py --dry-run --draft tasks/pending-emails/pavarini.md

Auth:
    Run email_auth_setup.py once to authenticate. Token cached in .claude/email-token-cache.json.
    If token expires, re-run email_auth_setup.py.

Draft file format:
    ---
    to: prospect@company.com
    from: wesley@caseglide.com
    subject: Re: Subject Line
    prospect: George Pavarini
    deal: Amerisure
    type: second_touch
    authorized: true
    ---

    Email body text here...

Environment:
    AZURE_CLIENT_ID — from .env.local (required)
    AZURE_TENANT_ID — from .env.local (required)
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path

import requests

try:
    import msal
except ImportError:
    print("ERROR: msal not installed. Run: pip3 install msal")
    sys.exit(1)

try:
    import yaml
except ImportError:
    yaml = None

# ── Paths ────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / "caseglide-platform" / ".env.local"
TOKEN_CACHE_FILE = PROJECT_ROOT / ".claude" / "email-token-cache.json"
PENDING_DIR = PROJECT_ROOT / "tasks" / "pending-emails"
SENT_DIR = PROJECT_ROOT / "tasks" / "sent-emails"
LOG_FILE = PROJECT_ROOT / "tasks" / "email-send-log.md"

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
SCOPES = ["Mail.Send", "Mail.ReadWrite"]

# Approved senders
APPROVED_SENDERS = {"wesley@caseglide.com", "lrodriguez@caseglide.com"}

logging.basicConfig(level=logging.INFO, format="[send_email] %(message)s")
log = logging.getLogger(__name__)


# ── Config ────────────────────────────────────────────────────────────────────

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


def get_config():
    env = load_env()
    client_id = os.environ.get("AZURE_CLIENT_ID") or env.get("AZURE_CLIENT_ID")
    tenant_id = os.environ.get("AZURE_TENANT_ID") or env.get("AZURE_TENANT_ID")

    if not client_id or not tenant_id:
        print("\nERROR: AZURE_CLIENT_ID and AZURE_TENANT_ID not configured.")
        print("Run: python3 scripts/email_auth_setup.py")
        sys.exit(1)

    return client_id, tenant_id


# ── Auth ──────────────────────────────────────────────────────────────────────

def get_token(client_id: str, tenant_id: str) -> str:
    """Get access token from cache or prompt re-auth."""
    cache = msal.SerializableTokenCache()

    if TOKEN_CACHE_FILE.exists():
        cache.deserialize(TOKEN_CACHE_FILE.read_text())

    app = msal.PublicClientApplication(
        client_id=client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        token_cache=cache,
    )

    accounts = app.get_accounts()
    result = None

    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])

    if not result:
        print("Token expired or missing. Re-run: python3 scripts/email_auth_setup.py")
        sys.exit(1)

    # Persist updated cache
    TOKEN_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_CACHE_FILE.write_text(cache.serialize())

    return result["access_token"]


# ── Draft parsing ─────────────────────────────────────────────────────────────

def parse_draft(path: Path) -> dict:
    """Parse a structured email draft markdown file."""
    content = path.read_text()

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            front = parts[1].strip()
            body = parts[2].strip()

            if yaml:
                meta = yaml.safe_load(front)
            else:
                # Minimal YAML parse
                meta = {}
                for line in front.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        meta[k.strip()] = v.strip()

            meta["body"] = body
            return meta

    raise ValueError(f"Draft {path} missing YAML frontmatter (--- block at top)")


# ── Email send ────────────────────────────────────────────────────────────────

def send_email(token: str, to: str, subject: str, body: str,
               sender: str = "wesley@caseglide.com",
               reply_to_message_id: str = None,
               dry_run: bool = False) -> bool:
    """Send an email via Microsoft Graph API."""

    if sender not in APPROVED_SENDERS:
        log.error(f"Sender {sender} not in approved list: {APPROVED_SENDERS}")
        return False

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    message = {
        "subject": subject,
        "body": {"contentType": "Text", "content": body},
        "toRecipients": [{"emailAddress": {"address": to}}],
    }

    if reply_to_message_id:
        # Threading: set in-reply-to header via singleValueExtendedProperties
        message["singleValueExtendedProperties"] = [
            {
                "id": "String 0x1042",  # PR_IN_REPLY_TO_ID
                "value": reply_to_message_id,
            }
        ]

    payload = {"message": message, "saveToSentItems": True}

    if dry_run:
        log.info(f"[DRY RUN] Would send:")
        log.info(f"  From: {sender}")
        log.info(f"  To: {to}")
        log.info(f"  Subject: {subject}")
        log.info(f"  Body preview: {body[:100]}...")
        return True

    url = f"{GRAPH_BASE}/users/{sender}/sendMail"
    resp = requests.post(url, headers=headers, json=payload, timeout=30)

    if resp.status_code == 202:
        log.info(f"SENT: {subject} → {to}")
        return True
    else:
        log.error(f"FAILED ({resp.status_code}): {resp.text[:300]}")
        return False


# ── Logging ───────────────────────────────────────────────────────────────────

def log_send(draft_meta: dict, subject: str, to: str, success: bool, dry_run: bool):
    """Append send record to email-send-log.md."""
    status = "DRY RUN" if dry_run else ("SENT" if success else "FAILED")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    prospect = draft_meta.get("prospect", to)
    deal = draft_meta.get("deal", "—")
    email_type = draft_meta.get("type", "follow_up")

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not LOG_FILE.exists():
        LOG_FILE.write_text("# Email Send Log\n\n| Timestamp | Status | Prospect | Deal | Type | To | Subject |\n|---|---|---|---|---|---|---|\n")

    with LOG_FILE.open("a") as f:
        f.write(f"| {ts} | {status} | {prospect} | {deal} | {email_type} | {to} | {subject} |\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Send emails via Microsoft Graph API")
    parser.add_argument("--draft", help="Path to draft markdown file")
    parser.add_argument("--to", help="Recipient email address")
    parser.add_argument("--subject", help="Email subject")
    parser.add_argument("--body", help="Email body text")
    parser.add_argument("--from", dest="sender", default="wesley@caseglide.com")
    parser.add_argument("--list", action="store_true", help="List pending draft files")
    parser.add_argument("--send-all", action="store_true", help="Send all authorized pending drafts")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # List pending drafts
    if args.list:
        PENDING_DIR.mkdir(parents=True, exist_ok=True)
        drafts = [f for f in PENDING_DIR.glob("*.md") if not f.name.startswith(".")]
        if not drafts:
            print("No pending email drafts.")
        else:
            print(f"{len(drafts)} pending draft(s):")
            for d in sorted(drafts):
                print(f"  {d.name}")
        return

    client_id, tenant_id = get_config()
    token = get_token(client_id, tenant_id)

    # Send all authorized pending drafts
    if args.send_all:
        PENDING_DIR.mkdir(parents=True, exist_ok=True)
        drafts = sorted(PENDING_DIR.glob("*.md"))
        sent = 0
        for draft_path in drafts:
            if draft_path.name.startswith("."):
                continue
            try:
                meta = parse_draft(draft_path)
                if str(meta.get("authorized", "")).lower() != "true":
                    log.info(f"SKIP {draft_path.name} — authorized: not set to true")
                    continue

                to = meta.get("to", "")
                subject = meta.get("subject", "(no subject)")
                body = meta.get("body", "")
                sender = meta.get("from", args.sender)

                if not to:
                    log.warning(f"SKIP {draft_path.name} — no 'to' address")
                    continue

                success = send_email(token, to, subject, body, sender, dry_run=args.dry_run)
                log_send(meta, subject, to, success, args.dry_run)

                if success and not args.dry_run:
                    SENT_DIR.mkdir(parents=True, exist_ok=True)
                    draft_path.rename(SENT_DIR / draft_path.name)
                    sent += 1

            except Exception as e:
                log.error(f"Error processing {draft_path.name}: {e}")

        print(f"[send_email] {'Would send' if args.dry_run else 'Sent'} {sent} email(s)")
        return

    # Send single draft file
    if args.draft:
        draft_path = Path(args.draft)
        if not draft_path.exists():
            print(f"ERROR: Draft file not found: {args.draft}")
            sys.exit(1)

        meta = parse_draft(draft_path)
        to = meta.get("to", "")
        subject = meta.get("subject", "(no subject)")
        body = meta.get("body", "")
        sender = meta.get("from", args.sender)

        if not to:
            print("ERROR: Draft missing 'to' address in frontmatter")
            sys.exit(1)

        success = send_email(token, to, subject, body, sender, dry_run=args.dry_run)
        log_send(meta, subject, to, success, args.dry_run)

        if success and not args.dry_run:
            SENT_DIR.mkdir(parents=True, exist_ok=True)
            draft_path.rename(SENT_DIR / draft_path.name)
        return

    # Send from direct args
    if args.to and args.subject and args.body:
        meta = {"type": "direct", "prospect": args.to, "deal": "—"}
        success = send_email(token, args.to, args.subject, args.body, args.sender,
                             dry_run=args.dry_run)
        log_send(meta, args.subject, args.to, success, args.dry_run)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
