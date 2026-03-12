# CaseGlide Outbound Campaign Tier Architecture
**Date:** 2026-03-12
**Status:** APPROVED
**Author:** COS (Chief of Staff)

---

## Overview

Restructure Apollo outbound from two loosely-defined campaigns into five precision-targeted tiers, each with a dedicated sequence and clean saved search. Tiers 1-3 and 5 reuse existing Campaign 1 email copy. Tier 4 (Guidewire ecosystem) is designed but held until partnership approval.

---

## Problem Statement

- Campaign 1 (GC/CLO, mixed industries): working well — 27.9% open, 4+ real replies — but audience is imprecise
- Campaign 2 (CRO/VP Risk): 3,735 contacts loaded from unknown source, no saved search, 43% on-target rate — scrapped
- No systematic, repeatable list-building process tied to a clear ICP hierarchy
- ~53K people in Apollo match ICP filters but haven't been converted to contacts yet

---

## ICP Hierarchy

| Tier | Persona | Company Filter | Title Filter |
|------|---------|---------------|--------------|
| 1 | Fortune 500 Legal | 10,000+ employees | General Counsel, Chief Legal Officer, VP Legal Operations, Deputy General Counsel |
| 2 | Fortune 500 Risk | 10,000+ employees | Chief Risk Officer, VP Risk Management, VP Litigation |
| 3 | Insurance Carrier Leadership | Insurance industry, 500+ employees | CEO, CFO, COO, General Counsel, Chief Claims Officer |
| 4 | Guidewire Ecosystem | Insurance/Insurtech | CIO, VP IT (carriers); Consultants (PwC, Deloitte, Big 4); Guidewire staff (CS, Sales, Partnerships) |
| 5 | Insurance Litigation | Insurance industry, 500+ employees | VP Litigation, VP of Litigation Management |

**Fortune 500 proxy:** 10,000+ employees filter. Apollo's F500 tag is unreliable via API.

**Tier 4 status:** On hold. Requires Guidewire partnership approval before any outreach. Sequence designed but not activated.

---

## Campaign-to-Sequence Mapping

| Tier | Apollo Sequence Name | Email Copy | Status |
|------|---------------------|-----------|--------|
| 1 | Tier 1 - F500 Legal (GC/CLO) | Campaign 1 copy (5 emails) | Create in Apollo UI |
| 2 | Tier 2 - F500 Risk (CRO/VP Risk) | Campaign 1 copy (5 emails) | Create in Apollo UI |
| 3 | Tier 3 - Insurance Leadership | Campaign 1 copy (5 emails) | Create in Apollo UI |
| 4 | Tier 4 - Guidewire Ecosystem | New copy (insurtech/integration angle) | Hold |
| 5 | Tier 5 - Insurance Litigation | Campaign 1 copy (5 emails) | Create in Apollo UI |

**Existing Campaign 1 (GC/CLO, mixed industries):** Stays active. Continues as-is.
**Existing Campaign 2:** Abandoned. Contacts left in place, sequence not activated.

**Note on copy reuse:** Campaign 1 emails were written for GC/CLO with a legal/nuclear-verdicts framing. Reusing them for Tiers 2, 3, and 5 is a deliberate fast-launch decision. If Tier 3 (insurance CEO/CFO) reply rate falls below 0.2% after 500+ delivered, revisit with persona-specific copy.

---

## List-Building Architecture

### Apollo Saved Searches (One-Time Setup)
Each tier maps to one Apollo saved search with exact filter criteria. Searches persist — new contacts enter the funnel automatically each week without rebuilding.

### Automated Weekly Pull (`weekly_list_build.py`)
- **Schedule:** Every Friday 10 AM
- **Per tier:** Pulls 400-500 new people matching saved search filters; executes in priority order (Tier 1 → 2 → 3 → 5)
- **Credit check:** Script pre-checks available Apollo email credits before any conversion. If remaining credits < weekly batch size, scales back the batch and logs a warning.
- **Weekly credit budget:** 500 credits/week total across all tiers (~125/tier). Current credit balance should be verified in Apollo account settings before launching Tiers 1-3+5.
- **Deduplication:** Excludes contacts already in any active sequence (`sequence_active_in_other_campaigns: true`)
- **Output:** `tasks/weekly-list-batch.json` + approval request in `tasks/pending-approvals.md`
- **Wes action:** Edit `[ ]` to `[Y]` in pending-approvals.md (~30 seconds)
- **Load:** Monday morning, contacts batch-added to respective sequences via API

### `campaign-criteria.md` Updates
Add Tier 1, 3, 4, 5 entries to match the new sequence IDs. Tier 2 entry already exists (update sequence_id).

---

## Deduplication Rules

- A contact can only be in one active sequence at a time
- Apollo enforces this automatically when `sequence_active_in_other_campaigns: true`
- Tier precedence for overlapping personas (e.g., GC at F500 insurance carrier): **Tier 1 wins** — enforced by running weekly pulls in priority order: Tier 1 → Tier 2 → Tier 3 → Tier 5. Higher-priority tiers claim contacts first; lower-priority tiers skip them via the active-sequence flag.
- Global exclusions enforced in `campaign-criteria.md`: Steve Kiernan, Peter Max Zimmerman, bounced/unsubscribed

---

## Tier 4 Activation Criteria

Tier 4 does not launch until ALL of the following are met:
1. Wes receives explicit approval from Guidewire partnership/marketing
2. Email copy is written to match Guidewire ecosystem hot topics (integration ROI, implementation success, marketplace positioning)
3. Sequence created in Apollo UI with new copy
4. CIO/VP IT list scoped separately from insurance consultant and Guidewire staff lists (different messaging angles)

---

## Metrics & Measurement

Separate sequences per tier enables clean per-tier analytics:
- Open rate, reply rate, bounce rate tracked independently
- If Tier 3 (insurance CEO) underperforms Tier 1 (F500 GC), diagnose and adjust messaging without touching other tiers
- Weekly digest (`scripts/daily_campaign_digest.py`) reports all active sequences

### Success Thresholds (per tier)
- Bounce rate: < 5% (pause and diagnose if exceeded)
- Open rate target: > 20%
- Reply rate target: > 0.3% (Campaign 1 baseline)

---

## One-Time Setup Required (Wes — ~1 hour in Apollo UI)

1. Create 4 new sequences in Apollo UI (Tiers 1, 2, 3, 5)
2. Paste Campaign 1's 5 emails into each sequence — copy is archived verbatim in `APOLLO_SEQUENCES_DRAFT.md` at the repo root
3. Set sender to Sarah Johnson on each
4. Activate each sequence
5. Paste the 4 new sequence IDs into `campaign-criteria.md`

After that: fully automated. No further Wes involvement in list building.

---

## Files Modified

| File | Change |
|------|--------|
| `campaign-criteria.md` | Add Tier 1, 3, 4 (disabled), 5 entries; update Tier 2 sequence_id |
| `scripts/weekly_list_build.py` | Support multiple campaign tiers from updated criteria file; add credit pre-check; enforce tier execution order |
| `scripts/daily_campaign_digest.py` | Update to pull metrics for all active sequences (currently hardcoded to Campaign 1 only) |
| `tasks/pending-approvals.md` | Receives weekly batch approval requests |
| `REVENUE.md` | Update campaign state after each tier launches |
