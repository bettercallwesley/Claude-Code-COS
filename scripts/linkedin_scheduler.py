#!/usr/bin/env python3
"""
linkedin_scheduler.py — Automated LinkedIn post scheduler via Buffer API.

Runs Mon/Wed/Fri at 7:30 AM. Cycles through 6 post templates, fills variables
from nuclear-verdicts.ts and newsletter-articles.ts, posts via Buffer.

Usage:
    python3 scripts/linkedin_scheduler.py [--dry-run]

Environment:
    BUFFER_ACCESS_TOKEN — required (add to caseglide-platform/.env.local)
    BUFFER_LINKEDIN_PROFILE_ID — required (add to caseglide-platform/.env.local)
"""

import os
import sys
import re
import json
import random
import argparse
from pathlib import Path
from datetime import datetime

import requests
from typing import Dict, List, Optional
import yaml

PROJECT_ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = PROJECT_ROOT / ".claude" / "templates" / "linkedin"
STATE_FILE = PROJECT_ROOT / "tasks" / "linkedin-state.md"
NUCLEAR_VERDICTS_FILE = PROJECT_ROOT / "caseglide-platform" / "src" / "data" / "nuclear-verdicts.ts"
ARTICLES_FILE = PROJECT_ROOT / "caseglide-platform" / "src" / "data" / "newsletter-articles.ts"

TEMPLATE_ORDER = [
    "data-point.md",
    "article-teaser.md",
    "client-outcome.md",
    "industry-observation.md",
    "verdict-case-study.md",
    "myth-misconception.md",
]

STATIC_TEMPLATES = {"industry-observation.md", "myth-misconception.md"}

PROOF_POINTS = [
    "25% reduction in defense spend",
    "10% reduction in settlement amounts",
    "25% drop in overall litigation volume",
]

BUFFER_BASE = "https://api.bufferapp.com/1"


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


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {"last_template_index": 0, "last_post_date": None, "used_verdict_ids": []}

    content = STATE_FILE.read_text()
    # Parse YAML frontmatter-style from the file
    state = {}
    for line in content.splitlines():
        if ":" in line and not line.startswith("#"):
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if val == "null":
                state[key] = None
            elif val.startswith("[") and val.endswith("]"):
                try:
                    state[key] = json.loads(val)
                except (json.JSONDecodeError, ValueError):
                    state[key] = []
            else:
                try:
                    state[key] = int(val)
                except ValueError:
                    state[key] = val
    return state


def save_state(state: dict) -> None:
    content = STATE_FILE.read_text() if STATE_FILE.exists() else ""
    lines = content.splitlines()

    updated_keys = set()
    new_lines = []

    for line in lines:
        if line.startswith("#") or not line.strip():
            new_lines.append(line)
            continue
        if ":" in line:
            key = line.split(":")[0].strip()
            if key in state:
                val = state[key]
                if val is None:
                    new_lines.append(f"{key}: null")
                elif isinstance(val, list):
                    new_lines.append(f"{key}: {json.dumps(val)}")
                else:
                    new_lines.append(f"{key}: {val}")
                updated_keys.add(key)
                continue
        new_lines.append(line)

    # Add any new keys not in original file
    for key, val in state.items():
        if key not in updated_keys:
            if val is None:
                new_lines.append(f"{key}: null")
            elif isinstance(val, list):
                new_lines.append(f"{key}: {json.dumps(val)}")
            else:
                new_lines.append(f"{key}: {val}")

    STATE_FILE.write_text("\n".join(new_lines) + "\n")


def parse_nuclear_verdicts() -> List[Dict]:
    """Extract state verdict records from nuclear-verdicts.ts using regex.

    Parses StateVerdictData format: id (state code), name, largestVerdict (millions), largestVerdictCase.
    Filters out states with no verdicts.
    """
    if not NUCLEAR_VERDICTS_FILE.exists():
        return []

    content = NUCLEAR_VERDICTS_FILE.read_text()

    verdicts = []
    # Match state data rows — format: id: "CA", name: "California", ..., largestVerdict: 2100, largestVerdictCase: "..."
    pattern = r'id:\s*"([A-Z]{2})",\s*name:\s*"([^"]+)"[^;]*?largestVerdict:\s*(\d+)[^;]*?largestVerdictCase:\s*"([^"]+)"'
    for match in re.finditer(pattern, content, re.DOTALL):
        largest_verdict = int(match.group(3))
        if largest_verdict < 10:  # Skip states with no meaningful verdicts
            continue
        # Extract case type from parenthetical in case name
        case_name = match.group(4)
        case_type_match = re.search(r'\(([^)]+)\)\s*$', case_name)
        case_type = case_type_match.group(1) if case_type_match else "civil litigation"

        verdicts.append({
            "id": match.group(1),
            "state": match.group(2),
            "amount": f"${largest_verdict}M",
            "case_type": case_type,
            "case_name": re.sub(r'\s*\([^)]+\)\s*$', '', case_name).strip(),
            "year": "2024/2025",
        })

    return verdicts


def parse_latest_article() -> Optional[Dict]:
    """Extract the most recent article from newsletter-articles.ts."""
    if not ARTICLES_FILE.exists():
        return None

    content = ARTICLES_FILE.read_text()

    # Find first article entry — look for slug, title, and hook
    slug_match = re.search(r'slug:\s*["\']([^"\']+)["\']', content)
    title_match = re.search(r'title:\s*["\']([^"\']+)["\']', content)

    # Hook is usually in the first paragraph block
    hook_match = re.search(r'type:\s*["\']paragraph["\'][^}]*?content:\s*["\']([^"\']{20,200})["\']', content, re.DOTALL)

    if not slug_match:
        return None

    slug = slug_match.group(1)
    title = title_match.group(1) if title_match else slug
    hook = hook_match.group(1) if hook_match else title

    return {
        "slug": slug,
        "title": title,
        "hook": hook[:200] + "..." if len(hook) > 200 else hook,
        "url": f"https://www.litigationsentinel.com/articles/{slug}"
    }


def get_unused_verdict(state: dict, verdicts: List[Dict]) -> Optional[Dict]:
    """Get a random verdict not yet used in recent posts."""
    used = set(state.get("used_verdict_ids", []))
    available = [v for v in verdicts if v["id"] not in used]

    if not available:
        # Reset if all have been used
        available = verdicts
        state["used_verdict_ids"] = []

    if not available:
        return None

    return random.choice(available)


def render_template(template_name: str, state: dict, verdict: Optional[Dict], article: Optional[Dict]) -> Optional[str]:
    """Fill template variables and return post text. Returns None if template should be skipped."""
    template_path = TEMPLATES_DIR / template_name
    if not template_path.exists():
        print(f"[linkedin_scheduler] Template not found: {template_name}")
        return None

    content = template_path.read_text()

    # Strip frontmatter comment lines (lines starting with #)
    lines = [l for l in content.splitlines() if not l.startswith("#")]
    text = "\n".join(lines).strip()

    # Check if static template still has placeholder
    if template_name in STATIC_TEMPLATES:
        if "PLACEHOLDER" in text:
            print(f"[linkedin_scheduler] SKIP: {template_name} — needs Wes to write static content")
            return None
        return text

    # Fill variables
    if verdict:
        text = text.replace("{{verdict_amount}}", verdict.get("amount", ""))
        text = text.replace("{{state}}", verdict.get("state", ""))
        text = text.replace("{{case_type}}", verdict.get("case_type", ""))
        text = text.replace("{{year}}", str(verdict.get("year", "")))
        text = text.replace("{{case_name}}", f"{verdict.get('case_type', '')} case")

    if article:
        text = text.replace("{{article_title}}", article.get("title", ""))
        text = text.replace("{{article_hook}}", article.get("hook", ""))
        text = text.replace("{{article_url}}", article.get("url", ""))

    # Proof point rotation based on template index
    proof_index = state.get("last_template_index", 0) % len(PROOF_POINTS)
    text = text.replace("{{proof_point}}", PROOF_POINTS[proof_index])

    return text


def post_to_buffer(token: str, profile_id: str, text: str) -> dict:
    """Send post to Buffer queue for LinkedIn."""
    resp = requests.post(
        f"{BUFFER_BASE}/updates/create.json",
        data={
            "access_token": token,
            "profile_ids[]": profile_id,
            "text": text,
            "scheduled_at": "now",
        }
    )
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="LinkedIn post scheduler via Buffer")
    parser.add_argument("--dry-run", action="store_true", help="Render post but do not send to Buffer")
    args = parser.parse_args()

    token = get_env("BUFFER_ACCESS_TOKEN")
    profile_id = get_env("BUFFER_LINKEDIN_PROFILE_ID")

    if not args.dry_run:
        if not token:
            print("[linkedin_scheduler] ERROR: BUFFER_ACCESS_TOKEN not set.")
            print("  Add to caseglide-platform/.env.local: BUFFER_ACCESS_TOKEN=your_token")
            sys.exit(1)
        if not profile_id:
            print("[linkedin_scheduler] ERROR: BUFFER_LINKEDIN_PROFILE_ID not set.")
            print("  Run: curl 'https://api.bufferapp.com/1/profiles.json?access_token=YOUR_TOKEN'")
            print("  Add the id field to .env.local: BUFFER_LINKEDIN_PROFILE_ID=...")
            sys.exit(1)

    state = load_state()
    verdicts = parse_nuclear_verdicts()
    article = parse_latest_article()
    verdict = get_unused_verdict(state, verdicts) if verdicts else None

    current_index = state.get("last_template_index", 0)
    template_name = TEMPLATE_ORDER[current_index % len(TEMPLATE_ORDER)]

    print(f"[linkedin_scheduler] Template: {template_name} (index {current_index})")
    if verdict:
        print(f"[linkedin_scheduler] Verdict: {verdict['amount']} — {verdict['state']} ({verdict['year']})")
    if article:
        print(f"[linkedin_scheduler] Article: {article['title']}")

    post_text = render_template(template_name, state, verdict, article)

    if post_text is None:
        # Skip this template, advance index and try next
        print(f"[linkedin_scheduler] Skipping template {template_name} — trying next")
        state["last_template_index"] = (current_index + 1) % len(TEMPLATE_ORDER)
        if not args.dry_run:
            save_state(state)
        return

    print(f"\n[linkedin_scheduler] Post preview (first 100 chars):")
    print(f"  {post_text[:100]}...")

    if args.dry_run:
        print("\n[DRY RUN] Post not sent to Buffer.")
        return

    result = post_to_buffer(token, profile_id, post_text)
    print(f"[linkedin_scheduler] Posted to Buffer: {result.get('success', False)}")

    # Update state
    state["last_template_index"] = (current_index + 1) % len(TEMPLATE_ORDER)
    state["last_post_date"] = datetime.now().isoformat()
    if verdict:
        used = state.get("used_verdict_ids", [])
        used.append(verdict["id"])
        state["used_verdict_ids"] = used

    save_state(state)
    print(f"[linkedin_scheduler] State updated — next template: {TEMPLATE_ORDER[state['last_template_index']]}")


if __name__ == "__main__":
    main()
