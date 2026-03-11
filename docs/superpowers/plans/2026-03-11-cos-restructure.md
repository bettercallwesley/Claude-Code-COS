# COS Restructure Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the COS from browser-dependent monitor to API-first autonomous executor across LinkedIn, Apollo, newsletter, and deal management.

**Architecture:** Six independent chunks executed in order. Chunks 1-2 are prerequisites. Chunks 3-5 can run in parallel after Chunk 2. Chunk 6 is one-time and independent.

**Tech Stack:** Claude Code scheduled tasks (mcp__scheduled-tasks), Python 3 scripts, Buffer API, Microsoft 365 MCP, Apollo API, Beehiiv API, Pipedrive API

**Spec:** `docs/superpowers/specs/2026-03-11-cos-restructure-design.md`

---

## Chunk 0: Prerequisites (Already Done / One-Time Setup)

- [x] Remove jailbreak block from `CLAUDE.md` lines 83-98 — **COMPLETED 2026-03-11**
- [ ] Install required Python libraries (run once):

```bash
pip3 install pyyaml requests
```

Expected: no errors.

---

## Chunk 1: Foundation — Email Approval Loop + Daily Digest

**Files:**
- Modify: `.claude/agents/marketing-agent.md`
- Modify: `.claude/agents/sales-agent.md`
- Modify: `CLAUDE.md`
- Create: `tasks/pending-approvals.md`
- Modify: scheduled task `morning-ops-brief` (via mcp__scheduled-tasks)
- Modify: `.claude/settings.local.json`

### Task 1.1: Validate Microsoft 365 MCP Email Send

- [ ] **Step 1:** Open Claude Code Desktop in the COS project directory
- [ ] **Step 2:** Run a test send via Microsoft 365 MCP:
  - Use `mcp__claude_ai_Microsoft_365__read_resource` or equivalent to confirm the MCP is connected
  - Send a test email to wesley@caseglide.com with subject `[COS TEST] Email loop validation`
  - Body: `Reply to this email with: 1Y`
- [ ] **Step 3:** Reply to the email from your Outlook inbox with `1Y`
- [ ] **Step 4:** In the same Claude Code session, use `mcp__claude_ai_Microsoft_365__outlook_email_search` to search for the reply:
  - Search term: `[COS TEST]`
  - Verify the reply body is found and `1Y` is parseable with regex `[0-9]+[YyNn]`
- [ ] **Step 5:** If validation passes — note "M365 MCP VALIDATED" in `tasks/pending-approvals.md`. If it fails — note the error and use file-based fallback (pending-approvals.md) for all approval steps in this plan.
- [ ] **Step 6:** Commit

```bash
git add tasks/pending-approvals.md
git commit -m "feat: validate M365 email approval loop"
```

---

### Task 1.2: Create Approval Loop Script

- [ ] **Step 1:** Create `scripts/approval_loop.py` — a reusable helper that all scheduled tasks will import:

```python
#!/usr/bin/env python3
"""
Approval loop helper for COS scheduled tasks.
Sends approval requests via email (M365 MCP) and reads replies.
Fallback: writes to tasks/pending-approvals.md
"""
import re
import json
from datetime import datetime, timedelta
from pathlib import Path

PENDING_FILE = Path(__file__).parent.parent / "tasks" / "pending-approvals.md"
APPROVAL_EMAIL = "wesley@caseglide.com"
APPROVAL_SUBJECT_PREFIX = "[COS APPROVAL NEEDED]"
TIMEOUT_HOURS = 24

def send_approval_request(decisions: list[dict]) -> str:
    """
    decisions: [{"id": 1, "text": "Load 412 contacts into Campaign 1?"}]
    Returns request_id (date string) for tracking.
    """
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    subject = f"{APPROVAL_SUBJECT_PREFIX} {date_str}"
    lines = [f"{d['id']}. {d['text']} (Y/N)" for d in decisions]
    body = "\n".join(lines)
    # Write fallback regardless of email success
    _write_pending(subject, decisions)
    return date_str

def parse_approval_reply(reply_body: str) -> dict[int, bool]:
    """
    Parses '1Y 2N 3Y' style replies.
    Returns {1: True, 2: False, 3: True}
    Partial replies: only matched items returned.
    """
    matches = re.findall(r'(\d+)\s*([YyNn])', reply_body)
    return {int(num): val.upper() == 'Y' for num, val in matches}

def _write_pending(subject: str, decisions: list[dict]):
    """Write decisions to pending-approvals.md as fallback."""
    PENDING_FILE.parent.mkdir(exist_ok=True)
    with open(PENDING_FILE, 'a') as f:
        f.write(f"\n## {subject}\n")
        for d in decisions:
            f.write(f"- [ ] {d['id']}. {d['text']}\n")
        f.write(f"*To approve: edit this file, change [ ] to [Y] or [N]*\n")

def read_file_approvals(subject_contains: str) -> dict[int, bool]:
    """Read approvals from pending-approvals.md (fallback mode)."""
    if not PENDING_FILE.exists():
        return {}
    content = PENDING_FILE.read_text()
    if subject_contains not in content:
        return {}
    results = {}
    for match in re.finditer(r'- \[([YyNn])\] (\d+)\.', content):
        results[int(match.group(2))] = match.group(1).upper() == 'Y'
    return results
```

- [ ] **Step 2:** Run a quick smoke test:

```bash
python3 -c "
from scripts.approval_loop import parse_approval_reply
assert parse_approval_reply('1Y 2N 3Y') == {1: True, 2: False, 3: True}
assert parse_approval_reply('1y') == {1: True}
assert parse_approval_reply('gibberish') == {}
print('PASS')
"
```

Expected: `PASS`

- [ ] **Step 3:** Commit

```bash
git add scripts/approval_loop.py
git commit -m "feat: add approval loop helper script"
```

---

### Task 1.3: Rebuild morning-ops-brief Scheduled Task

The existing `morning-ops-brief` task reads browser-scanned data. Replace with API-only version that writes `tasks/daily-digest.md`.

- [ ] **Step 1:** Read the current `morning-ops-brief` task definition via `mcp__scheduled-tasks__list_scheduled_tasks` to get its current ID and schedule.

- [ ] **Step 2:** Create `tasks/daily-digest.md` with the schema (empty placeholder):

```markdown
## Date: PLACEHOLDER
## Campaign Metrics
- Apollo Campaign 1: — delivered, —% open, —% bounce
- Apollo Campaign 2: — delivered, —% open, —% bounce
- Beehiiv subscribers: —
## Deal Status
## Pending Approvals
## Flags
```

- [ ] **Step 3:** Update the `morning-ops-brief` scheduled task prompt to this new version (use mcp__scheduled-tasks update or delete+recreate):

```
You are the morning ops brief agent for CaseGlide COS. Run every weekday at 7:30 AM.

STEP 1 — Pull Apollo campaign metrics:
Run: python3 scripts/daily_campaign_digest.py
Read the output. Extract: Campaign 1 delivered/open/bounce, Campaign 2 delivered/open/bounce.

STEP 2 — Pull Beehiiv subscriber count:
curl -s -H "Authorization: Bearer $BEEHIIV_API_KEY" \
  "https://api.beehiiv.com/v2/publications/$BEEHIIV_PUBLICATION_ID/subscriptions?limit=1" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('total_results','unknown'))"

STEP 3 — Check deal staleness:
Read STATUS.md deals section. For each active deal, check last action date.
Flag any deal where last action > 3 days ago.

STEP 4 — Write tasks/daily-digest.md with this exact schema:
## Date: {today}
## Campaign Metrics
- Apollo Campaign 1: {c1_delivered} delivered, {c1_open}% open, {c1_bounce}% bounce
- Apollo Campaign 2: {c2_delivered} delivered, {c2_open}% open, {c2_bounce}% bounce
- Beehiiv subscribers: {sub_count}
## Deal Status
{for each deal: "- {name}: last touch {date}, {N} days ago, stage: {stage}"}
## Pending Approvals
{read tasks/pending-approvals.md unchecked items, list them here}
## Flags
{list any: bounce >5%, open rate drop >20% WoW, deal >3 days, M365 email failures}

STEP 5 — Send iMessage to +18134802328 using Desktop Commander MCP tool
(mcp__Desktop_Commander__start_process with osascript command):
Message: "Morning brief ready. {N} flags. {N} pending approvals. See tasks/daily-digest.md"
Only send if flags or pending approvals exist. Silent success if all clear.
Note: Desktop Commander MCP is already permitted in .claude/settings.local.json.
```

- [ ] **Step 4:** Add required permissions to `.claude/settings.local.json` if not present:
```json
"Bash(python3 scripts/daily_campaign_digest.py*)",
"Bash(curl -s -H \"Authorization*\")"
```

- [ ] **Step 5:** Trigger the task manually once to verify it writes `daily-digest.md` correctly.

- [ ] **Step 6:** Commit

```bash
git add tasks/daily-digest.md .claude/settings.local.json
git commit -m "feat: rebuild morning-ops-brief as API-first digest writer"
```

---

## Chunk 2: Apollo Automation — List Building + Deal Watchdog

**Files:**
- Create: `campaign-criteria.md`
- Create: scheduled task `weekly-list-build` (new)
- Modify: scheduled task `deal-pipeline-watchdog`
- Modify: scheduled task `campaign-monitor`
- Modify: `.claude/settings.local.json`

### Task 2.1: Create campaign-criteria.md

- [ ] **Step 1:** Create `campaign-criteria.md` at project root:

```yaml
# Apollo Campaign Targeting Criteria
# Edit this file to change list-building behavior.
# Changes take effect at next Friday 10 AM list build.

campaign_1:
  description: "GC / CLO Cold Outreach"
  sequence_id: "699deee1299e51000d383130"
  titles:
    - "General Counsel"
    - "CLO"
    - "Chief Legal Officer"
    - "VP Legal"
    - "Litigation Manager"
    - "Deputy General Counsel"
    - "Senior Litigation Manager"
  industries:
    - "Insurance"
    - "Financial Services"
    - "Healthcare"
  min_employees: 500
  email_status: "verified"

campaign_2:
  description: "CRO / VP Risk Outreach"
  sequence_id: "69ab6d24c5f76f000d3141f3"
  titles:
    - "CRO"
    - "Chief Risk Officer"
    - "VP Risk"
    - "VP Claims"
    - "CCO"
    - "Chief Claims Officer"
    - "VP Risk Management"
  industries:
    - "Insurance"
    - "Financial Services"
    - "Healthcare"
  min_employees: 500
  email_status: "verified"

global_exclusions:
  - "Steve Kiernan"
  - "Peter Max Zimmerman"
```

- [ ] **Step 2:** Commit

```bash
git add campaign-criteria.md
git commit -m "feat: add campaign targeting criteria file"
```

---

### Task 2.2: Create weekly-list-build Scheduled Task

- [ ] **Step 1:** Create `scripts/weekly_list_build.py`:

```python
#!/usr/bin/env python3
"""
Weekly autonomous list builder for COS.
Runs every Friday 10 AM. Builds Apollo contact batches per campaign-criteria.md,
deduplicates against existing CRM contacts, emails Wes approval request.
"""
import os
import re
import sys
import json
import yaml
import time
import requests
from pathlib import Path

# Allow importing sibling scripts
sys.path.insert(0, str(Path(__file__).parent))
from approval_loop import send_approval_request

APOLLO_KEY = os.environ.get("APOLLO_API_KEY")
CRITERIA_FILE = Path(__file__).parent.parent / "campaign-criteria.md"
BASE_URL = "https://api.apollo.io/v1"

def load_criteria():
    """Parse YAML code block from campaign-criteria.md."""
    text = CRITERIA_FILE.read_text()
    match = re.search(r'```ya?ml\n(.*?)```', text, re.DOTALL)
    yaml_text = match.group(1) if match else text
    return yaml.safe_load(yaml_text)

def get_existing_contact_emails() -> set:
    """Pull all existing Apollo CRM contact emails for dedup."""
    emails = set()
    page = 1
    while True:
        resp = requests.post(f"{BASE_URL}/contacts/search",
            headers={"Content-Type": "application/json", "Cache-Control": "no-cache"},
            json={"api_key": APOLLO_KEY, "page": page, "per_page": 100})
        data = resp.json()
        contacts = data.get("contacts", [])
        if not contacts:
            break
        for c in contacts:
            if c.get("email"):
                emails.add(c["email"].lower())
        page += 1
        time.sleep(0.2)
    return emails

def search_new_contacts(criteria: dict, existing_emails: set) -> list:
    """Search Apollo for contacts matching criteria, excluding existing."""
    new_contacts = []
    page = 1
    while True:
        resp = requests.post(f"{BASE_URL}/mixed_people/search",
            headers={"Content-Type": "application/json", "Cache-Control": "no-cache"},
            json={
                "api_key": APOLLO_KEY,
                "page": page,
                "per_page": 100,
                "person_titles": criteria["titles"],
                "organization_industry_tag_ids": [],  # resolved via API separately
                "q_organization_num_employees_ranges": [f"{criteria['min_employees']},99999"],
                "email_status": [criteria["email_status"]],
            })
        data = resp.json()
        people = data.get("people", [])
        if not people:
            break
        for p in people:
            email = (p.get("email") or "").lower()
            if email and email not in existing_emails:
                new_contacts.append(p)
                existing_emails.add(email)  # prevent intra-batch dupes
        if len(new_contacts) >= 500:  # cap per campaign per week
            break
        page += 1
        time.sleep(0.2)
    return new_contacts

def main():
    criteria = load_criteria()
    existing = get_existing_contact_emails()

    batches = {}
    for campaign_key in ["campaign_1", "campaign_2"]:
        crit = criteria[campaign_key]
        contacts = search_new_contacts(crit, existing)
        batches[campaign_key] = {
            "count": len(contacts),
            "sequence_id": crit["sequence_id"],
            "description": crit["description"],
            "contacts": contacts,
        }
        print(f"{campaign_key}: {len(contacts)} new contacts found")

    # Write batch to file for loading step
    output_file = Path(__file__).parent.parent / "tasks" / "weekly-list-batch.json"
    with open(output_file, "w") as f:
        json.dump(batches, f, indent=2)

    # Send approval request
    decisions = [
        {"id": i+1, "text": f"Load {b['count']} contacts into {b['description']}?"}
        for i, (_, b) in enumerate(batches.items())
        if b["count"] > 0
    ]
    if decisions:
        send_approval_request(decisions)
        print(f"Approval request sent for {len(decisions)} campaigns")
    else:
        print("No new contacts found this week")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2:** Test the script with a dry run (read-only, no contacts loaded):

```bash
source caseglide-platform/.env.local && python3 scripts/weekly_list_build.py
```

Expected: prints contact counts for each campaign, writes `tasks/weekly-list-batch.json`, writes `tasks/pending-approvals.md` entry.

- [ ] **Step 3:** Create the `weekly-list-build` scheduled task via mcp__scheduled-tasks:
  - Schedule: `0 10 * * 5` (Friday 10 AM)
  - Prompt:
```
Run the weekly Apollo list build:
1. cd to /Users/wesleytodd/Desktop/Claude Code-COS
2. Run: source caseglide-platform/.env.local && python3 scripts/weekly_list_build.py
3. Report results via iMessage to +18134802328: "Weekly list build complete. {N} campaigns ready for approval. Check tasks/pending-approvals.md"

If script errors: iMessage +18134802328 with error summary.
```

- [ ] **Step 4:** Commit

```bash
git add scripts/weekly_list_build.py
git commit -m "feat: add weekly autonomous list builder"
```

---

### Task 2.3: Rebuild deal-pipeline-watchdog

- [ ] **Step 1:** Create `scripts/deal_watchdog.py`:

```python
#!/usr/bin/env python3
"""
Deal pipeline watchdog. Runs daily at 7 AM M-F.
Checks Pipedrive for deals with no activity in >3 days.
Drafts follow-up, emails Wes for send approval.
"""
import os
import sys
import requests
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from approval_loop import send_approval_request

PIPEDRIVE_TOKEN = os.environ.get("PIPEDRIVE_API_TOKEN")
BASE_URL = "https://api.pipedrive.com/v1"

def get_open_deals():
    resp = requests.get(f"{BASE_URL}/deals",
        params={"api_token": PIPEDRIVE_TOKEN, "status": "open", "limit": 50})
    return resp.json().get("data", []) or []

def get_last_activity_date(deal_id: int) -> datetime | None:
    resp = requests.get(f"{BASE_URL}/deals/{deal_id}/activities",
        params={"api_token": PIPEDRIVE_TOKEN, "done": 1, "limit": 1})
    activities = resp.json().get("data", []) or []
    if not activities:
        return None
    return datetime.fromisoformat(activities[0]["add_time"].replace("Z", "+00:00"))

def draft_followup(deal: dict) -> str:
    contact = deal.get("person_name", "the team")
    org = deal.get("org_name", "your organization")
    return (
        f"Hi {contact.split()[0]},\n\n"
        f"Wanted to follow up on our recent conversation about CaseGlide "
        f"and how we can help {org} reduce litigation costs.\n\n"
        f"Do you have 15 minutes this week to reconnect?\n\n"
        f"Best,\nWes"
    )

def main():
    deals = get_open_deals()
    stale = []
    cutoff = datetime.now().astimezone() - timedelta(days=3)

    for deal in deals:
        last = get_last_activity_date(deal["id"])
        if last is None or last < cutoff:
            days = (datetime.now().astimezone() - last).days if last else 99
            stale.append({"deal": deal, "days": days, "draft": draft_followup(deal)})

    if not stale:
        print("All deals active — no action needed")
        return

    # Write drafts to file
    output = Path(__file__).parent.parent / "tasks" / "deal-followup-drafts.md"
    with open(output, "w") as f:
        f.write(f"# Deal Follow-Up Drafts — {datetime.now().strftime('%Y-%m-%d')}\n\n")
        for i, item in enumerate(stale, 1):
            f.write(f"## {i}. {item['deal']['title']} ({item['days']} days since last touch)\n\n")
            f.write(f"**Draft:**\n```\n{item['draft']}\n```\n\n")

    # Send approval request
    decisions = [
        {"id": i+1, "text": f"Send follow-up to {s['deal']['title']} ({s['days']}d stale)? Draft in tasks/deal-followup-drafts.md"}
        for i, s in enumerate(stale)
    ]
    send_approval_request(decisions)
    print(f"Watchdog: {len(stale)} stale deals. Approval request sent.")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2:** Test with a dry run (requires PIPEDRIVE_API_TOKEN in .env.local):

```bash
source caseglide-platform/.env.local && python3 scripts/deal_watchdog.py
```

Expected: prints stale deal count, writes `tasks/deal-followup-drafts.md`.

- [ ] **Step 3:** Update `deal-pipeline-watchdog` scheduled task prompt to run this script instead of browser-based checks.

- [ ] **Step 4:** Add Pipedrive token to `.claude/settings.local.json` allowed env vars if needed.

- [ ] **Step 5:** Commit

```bash
git add scripts/deal_watchdog.py
git commit -m "feat: rebuild deal watchdog as Pipedrive API-first script"
```

---

## Chunk 3: LinkedIn Automation — Buffer + Templates

**Files:**
- Create: `.claude/templates/linkedin/` (6 files)
- Create: `tasks/linkedin-state.md`
- Create: `scripts/linkedin_scheduler.py`
- Create: scheduled task `linkedin-scheduler` (new)
- Modify: `.claude/settings.local.json`

### Task 3.1: Set Up Buffer Account + API Key

- [ ] **Step 1:** Go to buffer.com, create account, connect Wes's LinkedIn profile
- [ ] **Step 2:** In Buffer developer settings, create an API access token
- [ ] **Step 3:** Add to `caseglide-platform/.env.local`:
```
BUFFER_ACCESS_TOKEN=your_token_here
BUFFER_LINKEDIN_PROFILE_ID=your_profile_id_here
```
- [ ] **Step 4:** Test the connection:

```bash
source caseglide-platform/.env.local && \
curl -s "https://api.bufferapp.com/1/profiles.json?access_token=$BUFFER_ACCESS_TOKEN" \
| python3 -c "import sys,json; [print(p['id'], p['service'], p['formatted_username']) for p in json.load(sys.stdin)]"
```

Expected: shows LinkedIn profile ID and username.

- [ ] **Step 5:** Commit env var names (not values) to `.claude/settings.local.json` permissions.

---

### Task 3.2: Create LinkedIn Template Files

- [ ] **Step 1:** Create `.claude/templates/linkedin/` directory and 6 template files:

**`data-point.md`:**
```
{{verdict_amount}} nuclear verdict in {{state}}.

That's not an outlier — it's the new baseline for {{case_type}} litigation.

Claims teams that don't see it coming don't have the data to fight back.

What's your exposure look like in {{state}}?

#LitigationIntelligence #NuclearVerdicts #InsuranceClaims
```

**`article-teaser.md`:**
```
{{article_hook}}

We broke this down for litigation professionals: {{article_url}}

If you work in claims or risk, this one's worth 10 minutes.

#LitigationStrategy #RiskManagement #InsuranceLaw
```

**`client-outcome.md`:**
```
One of our clients just hit {{proof_point}}.

Not from a new strategy. From having better data than opposing counsel.

Information asymmetry is the real litigation problem. CaseGlide fixes it.

#LitigationIntelligence #CaseGlide #DefenseStrategy
```

**`industry-observation.md`:**
```
[STATIC — Wes writes this once per quarter. File contains the post text directly with no variables.]

Placeholder: Replace this entire file content with Wes's authored observation post.
```

**`verdict-case-study.md`:**
```
{{case_name}}: ${{verdict_amount}} in {{state}}.

{{case_type}} case. Defense had no visibility into plaintiff's litigation history, prior verdicts in the jurisdiction, or opposing counsel's win rate.

CaseGlide gives you that visibility before trial.

#NuclearVerdicts #LitigationIntelligence #{{state}}Litigation
```

**`myth-misconception.md`:**
```
[STATIC — Wes writes this once. File contains the post text directly with no variables.]

Placeholder: Replace this entire file content with Wes's authored myth/misconception post.
```

- [ ] **Step 2:** Create `tasks/linkedin-state.md`:

```markdown
# LinkedIn Scheduler State
last_template_index: 0
used_verdict_ids: []
last_post_date: null
```

- [ ] **Step 3:** Commit

```bash
git add .claude/templates/linkedin/ tasks/linkedin-state.md
git commit -m "feat: add LinkedIn post templates and state tracker"
```

---

### Task 3.3: Create linkedin-scheduler Script + Task

- [ ] **Step 1:** Create `scripts/linkedin_scheduler.py`:

```python
#!/usr/bin/env python3
"""
LinkedIn post scheduler. Runs Mon/Wed/Fri at 7:30 AM.
Fills template variables, posts via Buffer API.
"""
import os
import re
import json
import random
import requests
from datetime import datetime
from pathlib import Path

BUFFER_TOKEN = os.environ.get("BUFFER_ACCESS_TOKEN")
BUFFER_PROFILE_ID = os.environ.get("BUFFER_LINKEDIN_PROFILE_ID")
TEMPLATES_DIR = Path(__file__).parent.parent / ".claude" / "templates" / "linkedin"
STATE_FILE = Path(__file__).parent.parent / "tasks" / "linkedin-state.md"
VERDICTS_FILE = Path(__file__).parent.parent / "caseglide-platform" / "src" / "data" / "nuclear-verdicts.ts"
ARTICLES_FILE = Path(__file__).parent.parent / "caseglide-platform" / "src" / "data" / "newsletter-articles.ts"

TEMPLATES = [
    "data-point.md", "article-teaser.md", "client-outcome.md",
    "industry-observation.md", "verdict-case-study.md", "myth-misconception.md"
]

PROOF_POINTS = [
    "a 25% reduction in defense spend",
    "a 10% reduction in settlement amounts",
    "a 25% drop in overall litigation volume"
]

def load_state() -> dict:
    if not STATE_FILE.exists():
        return {"last_template_index": 0, "used_verdict_ids": [], "last_post_date": None}
    state = {}
    for line in STATE_FILE.read_text().splitlines():
        if ":" in line and not line.startswith("#"):
            k, v = line.split(":", 1)
            state[k.strip()] = v.strip()
    state["last_template_index"] = int(state.get("last_template_index", 0))
    state["used_verdict_ids"] = json.loads(state.get("used_verdict_ids", "[]"))
    return state

def save_state(state: dict):
    STATE_FILE.write_text(
        f"# LinkedIn Scheduler State\n"
        f"last_template_index: {state['last_template_index']}\n"
        f"used_verdict_ids: {json.dumps(state['used_verdict_ids'][-30:])}\n"
        f"last_post_date: {datetime.now().strftime('%Y-%m-%d')}\n"
    )

def get_next_template(state: dict) -> tuple[int, str]:
    idx = (state["last_template_index"] + 1) % len(TEMPLATES)
    template_path = TEMPLATES_DIR / TEMPLATES[idx]
    return idx, template_path.read_text()

def get_verdict_data(used_ids: list) -> dict:
    """Extract a nuclear verdict entry not recently used."""
    text = VERDICTS_FILE.read_text()
    # Parse id, state, amount, caseType from TypeScript data
    verdicts = re.findall(
        r'\{[^}]*id:\s*["\']?(\w+)["\']?[^}]*state:\s*["\']([^"\']+)["\']'
        r'[^}]*amount:\s*(\d+)[^}]*caseType:\s*["\']([^"\']+)["\']',
        text, re.DOTALL
    )
    available = [v for v in verdicts if v[0] not in used_ids]
    if not available:
        available = verdicts  # reset if all used
    v = random.choice(available)
    return {
        "id": v[0], "state": v[1],
        "verdict_amount": f"${int(v[2]):,}M" if int(v[2]) > 1000 else f"${v[2]}K",
        "case_type": v[3], "case_name": f"Recent {v[3]} Case"
    }

def get_article_data() -> dict:
    """Get most recent article from newsletter-articles.ts."""
    text = ARTICLES_FILE.read_text()
    slug_match = re.search(r"slug:\s*['\"]([^'\"]+)['\"]", text)
    title_match = re.search(r"title:\s*['\"]([^'\"]+)['\"]", text)
    hook_match = re.search(r"content:\s*['\"]([^'\"]{50,200})['\"]", text)
    return {
        "article_url": f"https://litigationsentinel.com/articles/{slug_match.group(1)}" if slug_match else "",
        "article_title": title_match.group(1) if title_match else "",
        "article_hook": hook_match.group(1)[:150] + "..." if hook_match else "",
    }

def fill_template(template: str, state: dict) -> tuple[str, dict]:
    verdict = get_verdict_data(state["used_verdict_ids"])
    article = get_article_data()
    proof_idx = state["last_template_index"] % len(PROOF_POINTS)
    filled = template \
        .replace("{{verdict_amount}}", verdict["verdict_amount"]) \
        .replace("{{state}}", verdict["state"]) \
        .replace("{{case_type}}", verdict["case_type"]) \
        .replace("{{case_name}}", verdict["case_name"]) \
        .replace("{{article_url}}", article["article_url"]) \
        .replace("{{article_title}}", article["article_title"]) \
        .replace("{{article_hook}}", article["article_hook"]) \
        .replace("{{proof_point}}", PROOF_POINTS[proof_idx])
    return filled, verdict

def post_to_buffer(text: str) -> bool:
    resp = requests.post(
        "https://api.bufferapp.com/1/updates/create.json",
        data={
            "access_token": BUFFER_TOKEN,
            "profile_ids[]": BUFFER_PROFILE_ID,
            "text": text,
            "scheduled_at": "now",
        }
    )
    return resp.status_code == 200

def main():
    state = load_state()
    template_idx, template = get_next_template(state)
    post_text, verdict = fill_template(template, state)

    if "[STATIC" in post_text or "Placeholder:" in post_text:
        print(f"Template {TEMPLATES[template_idx]} needs Wes to write static content. Skipping.")
        return

    success = post_to_buffer(post_text)
    if success:
        state["last_template_index"] = template_idx
        state["used_verdict_ids"].append(verdict["id"])
        save_state(state)
        print(f"Posted: {TEMPLATES[template_idx]}")
        print(f"Preview: {post_text[:100]}...")
    else:
        print(f"Buffer post failed. Check BUFFER_ACCESS_TOKEN.")
        exit(1)

if __name__ == "__main__":
    main()
```

- [ ] **Step 2:** Test with dry run (won't post if Buffer token not yet set):

```bash
source caseglide-platform/.env.local && python3 scripts/linkedin_scheduler.py
```

Expected: prints which template would be used + first 100 chars of post text. Or prints "needs Wes to write static content" for templates 4 and 6 until Wes fills them.

- [ ] **Step 3:** Create `linkedin-scheduler` scheduled task:
  - Schedule: `30 7 * * 1,3,5` (Mon/Wed/Fri 7:30 AM)
  - Prompt:
```
Run the LinkedIn scheduler:
1. cd /Users/wesleytodd/Desktop/Claude Code-COS
2. source caseglide-platform/.env.local && python3 scripts/linkedin_scheduler.py
3. If success: silent (no notification needed)
4. If error: iMessage +18134802328 with error message
```

- [ ] **Step 4:** Commit

```bash
git add scripts/linkedin_scheduler.py
git commit -m "feat: add LinkedIn autonomous post scheduler"
```

---

## Chunk 4: Newsletter — Beehiiv + Apollo Distribution

**Files:**
- Create: `.claude/templates/newsletter-template.md`
- Create: `scripts/newsletter_send.py`
- Create: scheduled task `newsletter-send` (new)

### Task 4.1: Create Newsletter Template

- [ ] **Step 1:** Create `.claude/templates/newsletter-template.md`:

```markdown
# Litigation Sentinel Newsletter
*{{date}}*

---

## {{data_point_headline}}

{{data_point_body}}

---

## Worth Reading: {{article_title}}

{{article_hook}}

[Read the full analysis →]({{article_url}})

---

**Two ways to go deeper:**

→ [Subscribe to Litigation Sentinel](https://litigationsentinel.com) for weekly intelligence
→ [Book an Executive Briefing](https://litigationsentinel.com/briefing) — see how your program compares

---
*CaseGlide Litigation Intelligence | Unsubscribe*
```

- [ ] **Step 2:** Commit

```bash
git add .claude/templates/newsletter-template.md
git commit -m "feat: add newsletter template"
```

---

### Task 4.2: Create newsletter-send Script + Task

- [ ] **Step 1:** Create `scripts/newsletter_send.py`:

```python
#!/usr/bin/env python3
"""
Biweekly newsletter sender. Runs every 2 weeks Tuesday 9 AM.
Sends to Beehiiv subscribers + loads eligible Apollo contacts
into Newsletter sequence.
"""
import os
import re
import json
import random
import requests
from datetime import datetime
from pathlib import Path

BEEHIIV_KEY = os.environ.get("BEEHIIV_API_KEY")
BEEHIIV_PUB_ID = os.environ.get("BEEHIIV_PUBLICATION_ID")
APOLLO_KEY = os.environ.get("APOLLO_API_KEY")
NEWSLETTER_SEQUENCE_ID = os.environ.get("APOLLO_NEWSLETTER_SEQUENCE_ID", "")  # set after creation

TEMPLATE_FILE = Path(__file__).parent.parent / ".claude" / "templates" / "newsletter-template.md"
VERDICTS_FILE = Path(__file__).parent.parent / "caseglide-platform" / "src" / "data" / "nuclear-verdicts.ts"
ARTICLES_FILE = Path(__file__).parent.parent / "caseglide-platform" / "src" / "data" / "newsletter-articles.ts"

def get_content() -> dict:
    """Pull latest verdict and article for newsletter content."""
    # Get latest article
    articles_text = ARTICLES_FILE.read_text()
    slug = re.search(r"slug:\s*['\"]([^'\"]+)['\"]", articles_text)
    title = re.search(r"title:\s*['\"]([^'\"]+)['\"]", articles_text)
    hook = re.search(r"content:\s*['\"]([^'\"]{80,300})['\"]", articles_text)

    # Get random verdict for data point
    verdicts_text = VERDICTS_FILE.read_text()
    verdicts = re.findall(
        r'amount:\s*(\d+)[^}]*state:\s*["\']([^"\']+)["\']', verdicts_text
    )
    v = random.choice(verdicts) if verdicts else ("500", "Florida")
    amount = f"${int(v[0]):,}M" if int(v[0]) > 999 else f"${v[0]}K"

    return {
        "date": datetime.now().strftime("%B %d, %Y"),
        "data_point_headline": f"${amount} Nuclear Verdict in {v[1]}",
        "data_point_body": f"A {amount} verdict in {v[1]} highlights the growing gap between carriers with litigation intelligence and those without. The difference is data.",
        "article_title": title.group(1) if title else "Latest Analysis",
        "article_hook": hook.group(1)[:200] if hook else "",
        "article_url": f"https://litigationsentinel.com/articles/{slug.group(1)}" if slug else "https://litigationsentinel.com",
    }

def render_template(content: dict) -> str:
    template = TEMPLATE_FILE.read_text()
    for key, val in content.items():
        template = template.replace(f"{{{{{key}}}}}", val)
    return template

def send_beehiiv(subject: str, body: str) -> bool:
    """Send broadcast to all Beehiiv subscribers."""
    resp = requests.post(
        f"https://api.beehiiv.com/v2/publications/{BEEHIIV_PUB_ID}/broadcasts",
        headers={"Authorization": f"Bearer {BEEHIIV_KEY}", "Content-Type": "application/json"},
        json={
            "subject": subject,
            "content": {"free": body},
            "send_at": "now",
            "status": "confirmed",
        }
    )
    return resp.status_code in (200, 201)

def get_enrolled_emails(sequence_id: str) -> set:
    """Get all email addresses currently enrolled in a given Apollo sequence."""
    emails = set()
    page = 1
    while True:
        resp = requests.post("https://api.apollo.io/v1/contacts/search",
            headers={"Content-Type": "application/json", "Cache-Control": "no-cache"},
            json={"api_key": APOLLO_KEY, "page": page, "per_page": 100,
                  "emailer_campaign_id": sequence_id})
        contacts = resp.json().get("contacts", [])
        if not contacts:
            break
        for c in contacts:
            if c.get("email"):
                emails.add(c["email"].lower())
        page += 1
        import time; time.sleep(0.2)
    return emails

def load_apollo_newsletter_contacts() -> int:
    """Find Apollo CRM contacts not in Campaign 1, 2, or Newsletter sequences and add to newsletter."""
    if not NEWSLETTER_SEQUENCE_ID:
        print("APOLLO_NEWSLETTER_SEQUENCE_ID not set — skipping Apollo distribution")
        return 0

    CAMPAIGN_1_ID = "699deee1299e51000d383130"
    CAMPAIGN_2_ID = "69ab6d24c5f76f000d3141f3"

    # Get emails already in any active sequence
    enrolled = (
        get_enrolled_emails(CAMPAIGN_1_ID) |
        get_enrolled_emails(CAMPAIGN_2_ID) |
        get_enrolled_emails(NEWSLETTER_SEQUENCE_ID)
    )

    # Get all CRM contacts not enrolled
    eligible_ids = []
    page = 1
    while True:
        resp = requests.post("https://api.apollo.io/v1/contacts/search",
            headers={"Content-Type": "application/json", "Cache-Control": "no-cache"},
            json={"api_key": APOLLO_KEY, "page": page, "per_page": 100})
        contacts = resp.json().get("contacts", [])
        if not contacts:
            break
        for c in contacts:
            if c.get("email", "").lower() not in enrolled:
                eligible_ids.append(c["id"])
        page += 1
        import time; time.sleep(0.2)

    if not eligible_ids:
        print("No new contacts eligible for newsletter sequence")
        return 0

    # Add to newsletter sequence in batches of 100
    loaded = 0
    for i in range(0, len(eligible_ids), 100):
        batch = eligible_ids[i:i+100]
        resp = requests.post(
            f"https://api.apollo.io/v1/emailer_campaigns/{NEWSLETTER_SEQUENCE_ID}/add_contact_ids",
            headers={"Content-Type": "application/json", "Cache-Control": "no-cache"},
            json={
                "api_key": APOLLO_KEY,
                "contact_ids": batch,
                "emailer_campaign_id": NEWSLETTER_SEQUENCE_ID,
                "send_email_from_email_account_id": "69a598bdfd80760021e01e93",
                "sequence_active_in_other_campaigns": True,
                "sequence_finished_in_other_campaigns": True,
            }
        )
        if resp.status_code == 200:
            loaded += len(batch)
    return loaded

def main():
    content = get_content()
    body = render_template(content)
    subject = f"Litigation Intelligence Digest — {content['date']}"

    print(f"Sending newsletter: {subject}")

    # Send to Beehiiv
    if send_beehiiv(subject, body):
        print("Beehiiv: sent")
    else:
        print("Beehiiv: FAILED")

    # Load Apollo contacts
    loaded = load_apollo_newsletter_contacts()
    print(f"Apollo newsletter sequence: {loaded} contacts loaded")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2:** Create the Newsletter sequence in Apollo UI:
  - Name: "Newsletter Distribution"
  - 1-step sequence: send newsletter template email
  - Sender: Sarah Johnson
  - Note the sequence ID, add to `.env.local` as `APOLLO_NEWSLETTER_SEQUENCE_ID`

- [ ] **Step 3:** Test dry run:

```bash
source caseglide-platform/.env.local && python3 scripts/newsletter_send.py
```

Expected: renders newsletter content to stdout, attempts Beehiiv send.

- [ ] **Step 4:** Create `newsletter-send` scheduled task:
  - Schedule: `0 9 1,15 * *` (1st and 15th of each month at 9 AM — approximates biweekly)
  - Prompt:
```
Run the newsletter send:
1. cd /Users/wesleytodd/Desktop/Claude Code-COS
2. source caseglide-platform/.env.local && python3 scripts/newsletter_send.py
3. On success: iMessage +18134802328 "Newsletter sent to Beehiiv + Apollo contacts"
4. On failure: iMessage +18134802328 with error details
```

- [ ] **Step 5:** Commit

```bash
git add scripts/newsletter_send.py
git commit -m "feat: add biweekly newsletter sender"
```

---

## Chunk 5: Subagent Restructure

**Files:**
- Modify: `.claude/agents/marketing-agent.md`
- Modify: `.claude/agents/sales-agent.md`
- Modify: `CLAUDE.md`

### Task 5.1: Rewrite marketing-agent.md

- [ ] **Step 1:** Replace `.claude/agents/marketing-agent.md` with the new outcome-accountable version:

```markdown
# Marketing Agent

## Identity
You are the Marketing Agent for CaseGlide LLC, reporting to the Chief of Staff.
You own top-of-funnel revenue execution. You are accountable to metrics, not task lists.

## Metrics You Own
- Contacts added to sequences per week: target 400-500
- LinkedIn posts published per week: target 3
- Newsletter sends per cadence: target 1 per 2 weeks
- Campaign bounce rate: must stay <5%

If any metric misses target 2 weeks in a row: diagnose root cause, redesign approach, report to COS with new plan.

## Autonomous Execution (No Wes Required)
- Weekly list build: runs Friday via `scripts/weekly_list_build.py`
- LinkedIn posting: runs Mon/Wed/Fri via `scripts/linkedin_scheduler.py`
- Newsletter distribution: runs biweekly via `scripts/newsletter_send.py`
- Campaign monitoring: check metrics, escalate only on threshold breach

## Requires Wes Approval (via email)
- Loading new contacts into sequences (Y/N per batch)
- Activating new campaign sequences
- Any spend >$500

## Tools & References
- Apollo API rules: `.claude/rules/apollo-operations.md`
- Campaign criteria: `campaign-criteria.md`
- Campaign script: `scripts/apollo_campaign_manager.py`
- List builder: `scripts/weekly_list_build.py`
- Approval helper: `scripts/approval_loop.py`
- LinkedIn templates: `.claude/templates/linkedin/`
- LinkedIn state: `tasks/linkedin-state.md`
- Newsletter template: `.claude/templates/newsletter-template.md`
- State files: `REVENUE.md`, `STATUS.md`

## Escalation Rules
- Bounce rate >5%: pause sequence, iMessage Wes immediately
- Open rate drops >20% WoW: flag in digest, propose copy change
- New inbound reply to campaign: draft response, email Wes for send approval
- Never send outbound from any address except sarahjohnson@trycaseglide.com (sequences)

## Approved Senders
- Sequences: Sarah Johnson <sarahjohnson@trycaseglide.com> (mailbox ID: 69a598bdfd80760021e01e93)
- Steve Kiernan: PERMANENTLY REMOVED from all outbound
```

- [ ] **Step 2:** Commit

```bash
git add .claude/agents/marketing-agent.md
git commit -m "refactor: rewrite marketing-agent with outcome accountability"
```

---

### Task 5.2: Rewrite sales-agent.md

- [ ] **Step 1:** Replace the Active Deals section with a dynamic instruction (deals come from STATUS.md, not hardcoded), and add metric accountability:

  Open `.claude/agents/sales-agent.md`. Replace the hardcoded "Active Deals" list and "Operating Rules" section with:

```markdown
## Metric You Own
- Days-since-last-touch on every active deal: target ≤3 days
- If any deal exceeds 3 days: draft follow-up, email Wes for send approval. Do not wait to be asked.

## Active Deals
Read from STATUS.md at session start. Do not use hardcoded deal list — it goes stale.

## Watchdog
`scripts/deal_watchdog.py` runs daily and drafts follow-ups automatically. Your job is to:
1. Ensure the watchdog is running (check tasks/deal-followup-drafts.md freshness)
2. Escalate to COS if any deal has been stale >7 days (watchdog should have caught it at 3)
3. Prepare meeting briefs, demo packages, RFP responses when COS delegates

## Escalation Rules
- Deal >3 days: watchdog handles. You escalate to COS if >7 days.
- New inbound from prospect: draft response immediately, email Wes for approval
- RFP deadline <7 days: flag to COS as urgent, begin response prep
- Strategic asks (pricing, legal, contract): escalate to Wes with recommendation + binary ask only
```

- [ ] **Step 2:** Commit

```bash
git add .claude/agents/sales-agent.md
git commit -m "refactor: rewrite sales-agent with metric accountability"
```

---

### Task 5.3: Update COS CLAUDE.md Session Start

- [ ] **Step 1:** In `CLAUDE.md`, update the Session Start Protocol section to the new lean version:

Replace:
```
## Session Start Protocol — Every Session, No Exceptions

1. Scan Microsoft Outlook Email — flag prospect replies, inbound targets, anything time-sensitive
2. Scan Microsoft Outlook Calendar — flag meetings in next 7 days needing prep
3. Scan Microsoft Teams - flag any important messages in the General Group Chat and any direct messages
4. Read STATUS.md — load full pipeline state
5. Read GAPS.md — load all open blockers
6. Run the diagnosis — identify highest-leverage action, delegate to correct subagent
7. Produce Morning Brief:
   - What happened since last session
   - What you're delegating today and to which subagent
   - What (if anything) requires Wes — stated as recommendation + binary ask
8. Execute your full autonomous list before surfacing anything to Wes
```

With:
```
## Session Start Protocol — Every Session, No Exceptions

1. Read tasks/daily-digest.md — load current metrics, flags, pending approvals
2. Read STATUS.md — verify deal state (digest may be stale on deals)
3. Run diagnosis: what is highest-leverage action available? Rank: revenue impact × urgency ÷ effort
4. Execute autonomous list FIRST — delegate to subagents, run scripts, act on flags
5. Surface to Wes ONLY: decisions requiring Wes's voice (send approval, strategic pivot, legal)
   Format: "I need yes or no on X so I can do Y." One ask. Recommendation included.
6. Session end: update STATUS.md, confirm all scripts/tasks ran, no open items without owner+deadline
```

- [ ] **Step 2:** Commit

```bash
git add CLAUDE.md
git commit -m "refactor: streamline COS session start to digest-first protocol"
```

---

## Chunk 6: Legacy List Audit (One-Time)

**Files:**
- Create: `scripts/legacy_list_audit.py`
- Create: scheduled task `legacy-list-audit` (one-time trigger)

### Task 6.1: Create legacy-list-audit Script

- [ ] **Step 1:** Create `scripts/legacy_list_audit.py`:

```python
#!/usr/bin/env python3
"""
One-time legacy list audit. Scans HubSpot + Desktop spreadsheets.
Extracts contacts matching campaign criteria, deduplicates against Apollo CRM.
Outputs audit report + emails Wes for import approval.
"""
import os
import re
import sys
import csv
import glob
import json
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from approval_loop import send_approval_request

APOLLO_KEY = os.environ.get("APOLLO_API_KEY")
HUBSPOT_TOKEN = os.environ.get("HUBSPOT_PRIVATE_APP_TOKEN", "")
DESKTOP = Path.home() / "Desktop"
OUTPUT_FILE = Path(__file__).parent.parent / "tasks" / "legacy-list-audit.md"

TARGET_TITLES = [
    "general counsel", "clo", "chief legal officer", "vp legal",
    "litigation manager", "vp claims", "vp risk", "cro", "cco",
    "chief risk officer", "chief claims officer"
]

def get_apollo_emails() -> set:
    """Get all existing Apollo CRM emails for dedup."""
    emails = set()
    page = 1
    while True:
        resp = requests.post("https://api.apollo.io/v1/contacts/search",
            headers={"Content-Type": "application/json", "Cache-Control": "no-cache"},
            json={"api_key": APOLLO_KEY, "page": page, "per_page": 100})
        contacts = resp.json().get("contacts", [])
        if not contacts:
            break
        for c in contacts:
            if c.get("email"):
                emails.add(c["email"].lower())
        page += 1
    return emails

def scan_spreadsheets() -> list:
    """Scan Desktop for CSV/XLSX files with contact data."""
    contacts = []
    patterns = [str(DESKTOP / "*.csv"), str(DESKTOP / "*.xlsx"), str(DESKTOP / "**/*.csv")]
    for pattern in patterns:
        for filepath in glob.glob(pattern, recursive=True):
            try:
                with open(filepath, newline='', encoding='utf-8-sig', errors='ignore') as f:
                    reader = csv.DictReader(f)
                    headers = [h.lower() for h in (reader.fieldnames or [])]
                    if not any(h in headers for h in ['email', 'e-mail', 'email address']):
                        continue
                    for row in reader:
                        # Find email, name, title columns
                        email = next((row[k] for k in row if 'email' in k.lower() and row[k]), None)
                        title = next((row[k] for k in row if 'title' in k.lower() and row[k]), "")
                        name = next((row[k] for k in row if 'name' in k.lower() and row[k]), "")
                        company = next((row[k] for k in row if 'company' in k.lower() and row[k]), "")
                        if email and any(t in title.lower() for t in TARGET_TITLES):
                            contacts.append({
                                "email": email.lower().strip(),
                                "name": name, "title": title, "company": company,
                                "source": Path(filepath).name
                            })
            except Exception as e:
                print(f"Skipping {filepath}: {e}")
    return contacts

def get_hubspot_contacts() -> list:
    """Export HubSpot contacts matching target titles."""
    if not HUBSPOT_TOKEN:
        print("HUBSPOT_PRIVATE_APP_TOKEN not set — skipping HubSpot")
        return []
    contacts = []
    after = None
    while True:
        params = {"limit": 100, "properties": "email,firstname,lastname,jobtitle,company"}
        if after:
            params["after"] = after
        resp = requests.get(
            "https://api.hubapi.com/crm/v3/objects/contacts",
            headers={"Authorization": f"Bearer {HUBSPOT_TOKEN}"},
            params=params
        )
        data = resp.json()
        for c in data.get("results", []):
            p = c.get("properties", {})
            title = p.get("jobtitle", "")
            email = p.get("email", "")
            if email and any(t in title.lower() for t in TARGET_TITLES):
                contacts.append({
                    "email": email.lower().strip(),
                    "name": f"{p.get('firstname','')} {p.get('lastname','')}".strip(),
                    "title": title,
                    "company": p.get("company", ""),
                    "source": "HubSpot"
                })
        paging = data.get("paging", {})
        after = paging.get("next", {}).get("after")
        if not after:
            break
    return contacts

def main():
    print("Loading Apollo CRM for dedup...")
    apollo_emails = get_apollo_emails()
    print(f"Apollo CRM: {len(apollo_emails)} existing contacts")

    print("Scanning Desktop spreadsheets...")
    spreadsheet_contacts = scan_spreadsheets()

    print("Fetching HubSpot contacts...")
    hubspot_contacts = get_hubspot_contacts()

    all_contacts = spreadsheet_contacts + hubspot_contacts
    # Dedup against Apollo + internal dupes
    seen = set(apollo_emails)
    new_contacts = []
    for c in all_contacts:
        if c["email"] not in seen:
            seen.add(c["email"])
            new_contacts.append(c)

    # Group by source
    by_source = {}
    for c in new_contacts:
        by_source.setdefault(c["source"], []).append(c)

    # Write audit report
    with open(OUTPUT_FILE, "w") as f:
        f.write(f"# Legacy List Audit — {__import__('datetime').datetime.now().strftime('%Y-%m-%d')}\n\n")
        f.write(f"**Total new qualified contacts:** {len(new_contacts)}\n\n")
        for source, contacts in by_source.items():
            f.write(f"## {source} ({len(contacts)} contacts)\n\n")
            for c in contacts[:5]:  # show 5 samples
                f.write(f"- {c['name']} | {c['title']} | {c['company']} | {c['email']}\n")
            if len(contacts) > 5:
                f.write(f"- ... and {len(contacts)-5} more\n")
            f.write("\n")

    # Save full list for import
    import_file = Path(OUTPUT_FILE).parent / "legacy-list-import.json"
    with open(import_file, "w") as f:
        json.dump(new_contacts, f, indent=2)

    print(f"Audit complete: {len(new_contacts)} new contacts across {len(by_source)} sources")
    print(f"Report: tasks/legacy-list-audit.md")

    # Send approval request
    if new_contacts:
        send_approval_request([{
            "id": 1,
            "text": f"Import {len(new_contacts)} legacy contacts into Apollo? (See tasks/legacy-list-audit.md for full report)"
        }])

if __name__ == "__main__":
    main()
```

- [ ] **Step 2:** Add HubSpot token to `.env.local` (if available):
```
HUBSPOT_PRIVATE_APP_TOKEN=your_token_here
```
Note: If HubSpot access is unavailable, script skips HubSpot and scans Desktop spreadsheets only.

- [ ] **Step 3:** Test dry run:

```bash
source caseglide-platform/.env.local && python3 scripts/legacy_list_audit.py
```

Expected: scans Desktop, fetches HubSpot (or skips), writes `tasks/legacy-list-audit.md` and `tasks/legacy-list-import.json`.

- [ ] **Step 4:** Create one-time scheduled task `legacy-list-audit`:
  - Schedule: run once manually (or set a one-time trigger)
  - Prompt:
```
Run the one-time legacy list audit:
1. cd /Users/wesleytodd/Desktop/Claude Code-COS
2. source caseglide-platform/.env.local && python3 scripts/legacy_list_audit.py
3. Email wes@caseglide.com: "Legacy audit complete. Found {N} qualified contacts. See tasks/legacy-list-audit.md. Approval request sent."
4. After running: delete or disable this scheduled task.
```

- [ ] **Step 5:** Commit

```bash
git add scripts/legacy_list_audit.py
git commit -m "feat: add one-time legacy list audit script"
```

---

## Final Verification Checklist

After all chunks are complete:

- [ ] `tasks/daily-digest.md` is being written daily by `morning-ops-brief`
- [ ] Email approval loop sends and receives (or fallback to pending-approvals.md confirmed working)
- [ ] `campaign-criteria.md` exists and is readable by `weekly_list_build.py`
- [ ] Buffer account connected, LinkedIn profile ID confirmed
- [ ] LinkedIn templates: all 6 files exist, templates 4+6 have real content from Wes
- [ ] `scripts/linkedin_scheduler.py` dry-run produces valid post text
- [ ] Newsletter template renders correctly with real data
- [ ] `deal_watchdog.py` reads Pipedrive open deals without error
- [ ] All new scheduled tasks visible in `mcp__scheduled-tasks__list_scheduled_tasks`
- [ ] All new scripts committed to git
- [ ] `git push origin main`
