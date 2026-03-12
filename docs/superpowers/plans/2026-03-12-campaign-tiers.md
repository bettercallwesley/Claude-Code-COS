# Campaign Tier Architecture Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure Apollo outbound from 2 loosely-defined campaigns into 5 precision-targeted tiers with automated weekly list building and per-tier metrics reporting.

**Architecture:** `campaign-criteria.md` is the single source of truth for all tier definitions. `weekly_list_build.py` reads it in priority order, pre-checks credits, and batches new contacts for approval. `daily_campaign_digest.py` reads the same file to report all active sequences.

**Tech Stack:** Python 3.8, Apollo API v1, YAML (via PyYAML), requests

**Spec:** `docs/superpowers/specs/2026-03-12-campaign-tiers-design.md`

---

## Chunk 0: Update campaign-criteria.md

**Files:**
- Modify: `campaign-criteria.md`

### Task 0: Add tier priority order + new tier entries

- [ ] **Step 1: Open `campaign-criteria.md` and add `tier_priority` key**

Add this block directly after `global_exclusions:` section and before `campaigns:`:

```yaml
# Processing order for weekly_list_build.py — higher tiers claim contacts first
tier_priority:
  - tier_1_f500_legal
  - tier_2_f500_risk
  - tier_3_insurance_leadership
  - tier_5_insurance_litigation
  # tier_4_guidewire intentionally excluded — on hold pending partnership approval
```

- [ ] **Step 2: Replace existing `campaign_2_cro_vp_risk` entry**

First, **delete the entire `campaign_2_cro_vp_risk:` block** from `campaign-criteria.md` (the full block under that key). Then add the new `tier_2_f500_risk` entry in its place:

```yaml
  tier_2_f500_risk:
    name: "Tier 2 - F500 Risk (CRO / VP Risk)"
    sequence_id: null  # Set after creating sequence in Apollo UI
    mailbox_id: "69a598bdfd80760021e01e93"
    sender: "Sarah Johnson <sarahjohnson@trycaseglide.com>"
    weekly_cap: 125
    titles:
      - "Chief Risk Officer"
      - "VP Risk Management"
      - "Vice President of Risk Management"
      - "VP of Risk"
      - "Vice President of Risk"
      - "VP Litigation"
      - "Vice President of Litigation"
      - "VP of Litigation"
    min_employees: 10000
    contact_email_status:
      - "verified"
    person_locations:
      - "United States"
```

- [ ] **Step 3: Add `tier_1_f500_legal` entry**

```yaml
  tier_1_f500_legal:
    name: "Tier 1 - F500 Legal (GC / CLO)"
    sequence_id: null  # Set after creating sequence in Apollo UI
    mailbox_id: "69a598bdfd80760021e01e93"
    sender: "Sarah Johnson <sarahjohnson@trycaseglide.com>"
    weekly_cap: 125
    titles:
      - "General Counsel"
      - "Chief Legal Officer"
      - "Deputy General Counsel"
      - "VP Legal Operations"
      - "Vice President Legal Operations"
      - "VP of Legal Operations"
    min_employees: 10000
    contact_email_status:
      - "verified"
    person_locations:
      - "United States"
```

- [ ] **Step 4: Add `tier_3_insurance_leadership` entry**

```yaml
  tier_3_insurance_leadership:
    name: "Tier 3 - Insurance Leadership (CEO / CFO / COO)"
    sequence_id: null  # Set after creating sequence in Apollo UI
    mailbox_id: "69a598bdfd80760021e01e93"
    sender: "Sarah Johnson <sarahjohnson@trycaseglide.com>"
    weekly_cap: 125
    titles:
      - "Chief Executive Officer"
      - "CEO"
      - "Chief Financial Officer"
      - "CFO"
      - "Chief Operating Officer"
      - "COO"
      - "General Counsel"
      - "Chief Legal Officer"
      - "Chief Claims Officer"
    industries:
      - "Insurance"
    min_employees: 500
    contact_email_status:
      - "verified"
    person_locations:
      - "United States"
```

- [ ] **Step 5: Add `tier_5_insurance_litigation` entry**

```yaml
  tier_5_insurance_litigation:
    name: "Tier 5 - Insurance Litigation (VP Litigation)"
    sequence_id: null  # Set after creating sequence in Apollo UI
    mailbox_id: "69a598bdfd80760021e01e93"
    sender: "Sarah Johnson <sarahjohnson@trycaseglide.com>"
    weekly_cap: 125
    titles:
      - "VP Litigation"
      - "Vice President of Litigation"
      - "VP of Litigation Management"
      - "Vice President Litigation Management"
      - "Director of Litigation"
    industries:
      - "Insurance"
    min_employees: 500
    contact_email_status:
      - "verified"
    person_locations:
      - "United States"
```

- [ ] **Step 6: Add `tier_4_guidewire` entry (disabled)**

```yaml
  tier_4_guidewire:
    name: "Tier 4 - Guidewire Ecosystem (ON HOLD)"
    sequence_id: null  # DO NOT SET — on hold pending Guidewire partnership approval
    enabled: false
    mailbox_id: "69a598bdfd80760021e01e93"
    sender: "Sarah Johnson <sarahjohnson@trycaseglide.com>"
    weekly_cap: 125
    titles:
      - "Chief Information Officer"
      - "VP Information Technology"
      - "Vice President of IT"
      - "VP of IT"
    industries:
      - "Insurance"
    min_employees: 500
    contact_email_status:
      - "verified"
    person_locations:
      - "United States"
```

- [ ] **Step 7: Verify YAML parses cleanly**

```bash
cd "/Users/wesleytodd/Desktop/Claude Code-COS" && python3 -c "
import yaml, re
content = open('campaign-criteria.md').read()
yaml_lines = [l for l in content.splitlines() if not l.startswith('#')]
data = yaml.safe_load('\n'.join(yaml_lines))
print('Campaigns:', list(data['campaigns'].keys()))
print('Tier priority:', data.get('tier_priority'))
"
```

Expected: All 6 campaign keys printed, tier_priority list with 4 entries (no tier_4).

- [ ] **Step 8: Commit**

```bash
cd "/Users/wesleytodd/Desktop/Claude Code-COS"
git add campaign-criteria.md
git commit -m "Add 5-tier campaign criteria with priority order"
```

---

## Chunk 1: Update weekly_list_build.py

**Files:**
- Modify: `scripts/weekly_list_build.py`

Two changes: (1) process campaigns in `tier_priority` order instead of dict key order, (2) add credit pre-check with graceful cap-back.

### Task 1: Priority-ordered processing

- [ ] **Step 1: Replace the campaign key resolution in `main()`**

Find this block in `main()`:

```python
campaign_keys = [args.campaign] if args.campaign else list(criteria["campaigns"].keys())
```

Replace with:

```python
if args.campaign:
    campaign_keys = [args.campaign]
else:
    # Use tier_priority for deterministic order — higher tiers claim contacts first
    priority_order = criteria.get("tier_priority", list(criteria["campaigns"].keys()))
    campaign_keys = [k for k in priority_order if k in criteria["campaigns"]]
    # Append any campaigns not in priority list (shouldn't happen, but safe fallback)
    for k in criteria["campaigns"]:
        if k not in campaign_keys:
            campaign_keys.append(k)
```

- [ ] **Step 2: Add `enabled` flag check**

In the `for campaign_key in campaign_keys:` loop, after the `sequence_id` check, add:

```python
if not campaign.get("enabled", True):
    print(f"[weekly_list_build] SKIP {campaign_key} — disabled in campaign-criteria.md")
    continue
```

This makes `tier_4_guidewire` silently skip even if someone accidentally sets a sequence_id.

### Task 2: Credit pre-check

Apollo's API doesn't expose credit balance directly on the same key. We implement a soft cap: compute total contacts requested across all tiers, warn if it exceeds a configurable weekly budget, and scale back proportionally.

- [ ] **Step 3: Add credit budget constant near the top of the file (after imports)**

```python
# Weekly email credit budget — contacts discovered require 1 credit each to convert
WEEKLY_CREDIT_BUDGET = 500
```

- [ ] **Step 4: Add `check_credit_budget()` function**

Add after `get_api_key()`:

```python
def check_credit_budget(criteria: dict, campaign_keys: List[str]) -> float:
    """Compute total contacts requested this week and warn if over budget.

    Returns a float scale factor (0.0–1.0). Multiply each campaign's weekly_cap
    by this factor to stay within WEEKLY_CREDIT_BUDGET.
    Apollo doesn't expose credit balance via API — this is a soft guard.
    """
    total_requested = sum(
        criteria["campaigns"][k].get("weekly_cap", 500)
        for k in campaign_keys
        if k in criteria["campaigns"] and criteria["campaigns"][k].get("sequence_id")
    )

    if total_requested > WEEKLY_CREDIT_BUDGET:
        scale = WEEKLY_CREDIT_BUDGET / total_requested
        print(
            f"[weekly_list_build] WARNING: Total requested ({total_requested}) exceeds "
            f"weekly budget ({WEEKLY_CREDIT_BUDGET}). Scaling caps by {scale:.0%}."
        )
        return scale

    print(f"[weekly_list_build] Credit check: {total_requested} contacts requested, "
          f"{WEEKLY_CREDIT_BUDGET} budget — OK")
    return 1.0
```

- [ ] **Step 5: Apply scale factor in `main()` before the batch loop**

After `existing_emails = get_existing_contact_emails(api_key)`, add:

```python
# Pre-check credit budget — scale caps if total exceeds weekly budget
active_keys = [k for k in campaign_keys if criteria["campaigns"].get(k, {}).get("sequence_id")]
credit_scale = check_credit_budget(criteria, active_keys)
```

Then in the loop, replace:

```python
weekly_cap = campaign.get("weekly_cap", 500)
```

with:

```python
weekly_cap = int(campaign.get("weekly_cap", 500) * credit_scale)
```

- [ ] **Step 6: Fix Python 3.8 type hints (two locations)**

Change line 61:
```python
def get_existing_contact_emails(api_key: str) -> set[str]:
```
to:
```python
def get_existing_contact_emails(api_key: str) -> set:
```

Change line 120:
```python
def build_batch(api_key: str, criteria: dict, existing_emails: set[str],
```
to:
```python
def build_batch(api_key: str, criteria: dict, existing_emails: set,
```

(Python 3.8 doesn't support `set[str]` subscript syntax — use plain `set`)

- [ ] **Step 7: Test dry-run with new criteria**

```bash
cd "/Users/wesleytodd/Desktop/Claude Code-COS"
python3 scripts/weekly_list_build.py --dry-run
```

Expected output:
- Credit check line showing total requested vs budget
- SKIP messages for all tiers with `sequence_id: null`
- No batch written

- [ ] **Step 8: Test with a single campaign that has a real sequence_id**

```bash
python3 scripts/weekly_list_build.py --dry-run --campaign campaign_1_gc_clo
```

Expected: Searches Apollo, returns contacts sample, no file write.

- [ ] **Step 9: Commit**

```bash
git add scripts/weekly_list_build.py
git commit -m "weekly_list_build: priority-ordered tiers + credit budget guard"
```

---

## Chunk 2: Update daily_campaign_digest.py

**Files:**
- Modify: `scripts/daily_campaign_digest.py`

Current script is hardcoded to one campaign. Refactor to read all active sequences from `campaign-criteria.md` and report each.

### Task 3: Multi-campaign digest

- [ ] **Step 1: Add imports and criteria loader at top of file**

After existing imports, add:

```python
import re
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

CRITERIA_FILE = os.path.join(PROJECT_ROOT, "campaign-criteria.md")
```

- [ ] **Step 2: Add `load_active_campaigns()` function**

Add after `load_env()`:

```python
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

    # Fallback if nothing active
    if not active:
        active = [("campaign_1_gc_clo", {"name": CAMPAIGN_NAME, "sequence_id": DEFAULT_CAMPAIGN_ID})]

    return active
```

- [ ] **Step 3: Refactor `build_digest()` to accept a list of metrics**

Replace the existing `build_digest(apollo_metrics, beehiiv_data, date_str)` signature and body with:

```python
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
```

- [ ] **Step 4: Update `main()` to loop all active campaigns**

Replace lines 237–240 in the existing `main()` (the `campaign_raw = fetch_apollo_campaign(...)` and `apollo_metrics = parse_apollo_metrics(...)` lines) AND the `digest = build_digest(apollo_metrics, ...)` call on line 249 with the following block:

```python
# Determine which campaigns to report
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
            # Use the name from criteria, not Apollo's stored name
            metrics["name"] = camp.get("name", metrics["name"])
        all_apollo_metrics.append(metrics)
        time.sleep(0.2)  # Avoid rate limiting
```

Add `import time` at the top if not already present (it's already there in weekly_list_build.py but not in this file).

Note: `build_digest(all_apollo_metrics, ...)` is already called inline in the block above — do not add a separate Step 5 call.

- [ ] **Step 6: Add `import time` to imports**

Check the top of `daily_campaign_digest.py`. Add `import time` after the existing imports if missing.

- [ ] **Step 7: Test the updated script**

```bash
cd "/Users/wesleytodd/Desktop/Claude Code-COS"
python3 scripts/daily_campaign_digest.py
```

Expected: Digest with "Tier 1 - F500 Legal (GC/CLO)" section showing campaign metrics, plus Beehiiv section. Only campaigns with `sequence_id` set will appear — currently just Campaign 1.

Once Tiers 1-5 have sequence IDs set, they appear automatically.

- [ ] **Step 8: Commit**

```bash
git add scripts/daily_campaign_digest.py
git commit -m "daily_campaign_digest: report all active tiers from campaign-criteria.md"
```

---

## Chunk 3: Manual Apollo UI Setup (Wes — ~1 hour)

This chunk is not code. It's the one-time human step that activates the automation.

### Task 4: Create 4 sequences in Apollo UI

Email copy for all steps is archived verbatim in `APOLLO_SEQUENCES_DRAFT.md` at the repo root.

- [ ] **Step 1: Go to app.apollo.io → Sequences → New Sequence**

Create each of these 4 sequences. For each:
1. Name it exactly as shown below
2. Add 5 email steps (Day 1, 3, 6, 9, 14) — use **Campaign 1 copy only** from `APOLLO_SEQUENCES_DRAFT.md` (the first 5-step sequence block at the top of the file, labeled "Campaign 1 — GC/CLO Cold Outreach"). Do NOT use the Campaign 2 draft copy lower in the file.
3. Set sender: **Sarah Johnson** (sarahjohnson@trycaseglide.com)
4. Disable click tracking on all steps
5. Activate the sequence
6. Copy the sequence ID from the URL (format: `69xxxxxxxxxxxxxxxxxx`)

| Sequence to Create | campaign-criteria.md key |
|-------------------|--------------------------|
| Tier 1 - F500 Legal (GC/CLO) | `tier_1_f500_legal` |
| Tier 2 - F500 Risk (CRO/VP Risk) | `tier_2_f500_risk` |
| Tier 3 - Insurance Leadership | `tier_3_insurance_leadership` |
| Tier 5 - Insurance Litigation | `tier_5_insurance_litigation` |

- [ ] **Step 2: Paste sequence IDs into `campaign-criteria.md`**

For each sequence created, replace `sequence_id: null` with the actual ID:

```yaml
sequence_id: "69xxxxxxxxxxxxxxxxxx"
```

- [ ] **Step 3: Verify weekly_list_build.py picks them up**

```bash
python3 scripts/weekly_list_build.py --dry-run
```

Expected: No more SKIP messages for the tiers with IDs set. Should see Apollo people search results and contact previews for each active tier.

- [ ] **Step 4: Verify daily_campaign_digest.py reports them**

```bash
python3 scripts/daily_campaign_digest.py
```

Expected: One section per active tier in the digest output.

- [ ] **Step 5: Commit updated campaign-criteria.md with real sequence IDs**

```bash
git add campaign-criteria.md
git commit -m "Set sequence IDs for Tiers 1-3, 5 — all tiers live"
git push origin main
```

---

## Post-Launch Checklist

After all 4 sequences are created and IDs set:

- [ ] Run `python3 scripts/weekly_list_build.py --dry-run` — confirm all 4 tiers search Apollo
- [ ] Confirm total weekly contact count ≤ 500 (credit budget)
- [ ] Run `python3 scripts/daily_campaign_digest.py` — confirm all tiers appear in output
- [ ] Push all changes: `git push origin main`
