# COS Restructure Design
**Date:** 2026-03-11
**Status:** Approved
**Goal:** Maximize CaseGlide revenue with ≤1 hour/day of Wes's time by rebuilding the COS from monitor to executor.

---

## Problem Statement

The current COS architecture is:
- **Browser-dependent:** Most scheduled tasks require Chrome open with Outlook + Gmail signed in, blocking all automation when Wes is unavailable
- **Operations-focused:** Scheduled tasks produce reports and logs, not outcomes
- **Approval-heavy:** LinkedIn posts, newsletter sends, Apollo list loads all require Wes to be present and approving in real-time
- **Domain-oriented:** Subagents are accountable to task completion, not revenue metrics

Result: 0 Executive Briefings scheduled, 9 newsletter subscribers vs 100 target, active deals going dark — despite functional infrastructure.

---

## Design Principles

1. **API-first by default.** Every scheduled task must execute without a browser. Browser is fallback only for actions with no API equivalent.
2. **Template-locked execution.** Wes approves templates and topics once. COS executes indefinitely within those guardrails. No per-piece content approval.
3. **Batch async approval.** When COS needs Wes, it batches into a single daily email: decisions only, binary, no context required. Wes replies Y/N. COS reads reply via Microsoft 365 MCP.
4. **Outcome accountability.** Subagents own metrics, not task lists. COS redesigns any approach that misses its number.

---

## Operating Model

### Session Flow (Redesigned)

**Old:** Scan email + calendar + Teams + 6 state files → delegate → produce morning brief → wait for Wes
**New:** Read single digest file → run diagnosis → execute autonomous list → email Wes with 0-3 binary decisions

### Wes's Required Involvement

| Action | Current | Target |
|--------|---------|--------|
| LinkedIn post approval | Every post | Never (template-locked) |
| Apollo list approval | Manual | One email reply per batch |
| Newsletter approval | Every send | Never (template-locked) |
| Deal follow-up drafts | Review each | Only if deal >$50K or unusual |
| Campaign activation | UI login required | One email reply |
| Daily time required | 1-3 hours | ≤1 hour |

### Approval Loop — Email via Microsoft 365 MCP

When COS needs a decision:
1. Composes email to wesley@caseglide.com with subject `[COS APPROVAL NEEDED] {date}`
2. Body lists numbered decisions: `1. Load 412 GC/CLO contacts into Campaign 1? (Y/N)`
3. For deal follow-up approvals, the full draft is included below the decision line: `1. Send follow-up to Jason Winnell (Hartford)? (Y/N)\n---\n[draft email body]`
4. Wes replies with decision codes: `1Y`, `2N 3Y`, etc.
5. Next scheduled task reads reply via `mcp__claude_ai_Microsoft_365__outlook_email_search`, searching for most recent email with subject containing `[COS APPROVAL NEEDED]`, parses codes from reply body
6. Timeout: 24 hours — unanswered items are skipped and flagged in next digest

**Reply parsing rules:**
- Match pattern `[0-9]+[YyNn]` in reply body, ignore everything else
- Partial reply (e.g., Wes replies `1Y` when 3 decisions were sent): only item 1 executes, items 2-3 skip and re-queue for next digest
- Malformed reply (no parseable codes found): all items skip, all flagged in next digest
- Multiple matching threads: use most recent email only

**Dependency:** Microsoft 365 MCP email send/receive must be validated end-to-end before this loop is trusted. Until validated, COS writes decisions to `tasks/pending-approvals.md` as fallback.

---

## Execution Architecture

### Channel 1: LinkedIn — Fully Autonomous Posting

**Current state:** Wes drafts, approves, and manually posts. Calendar exists but depends on Wes remembering.

**New model:**
- Template library: 6 markdown files in `.claude/templates/linkedin/`
- Posts scheduled via **Buffer API** (decision: Buffer over native LinkedIn API — simpler OAuth, supports scheduling)
- Cadence: Mon/Wed/Fri 7:30 AM, no Wes involvement
- Wes receives weekly performance summary via email only

**Template rotation:** Sequential, cycling 1-6. State tracked in `tasks/linkedin-state.md` (fields: `last_template_index`, `used_verdict_ids[]`).

**Variable sources:**
- `{{verdict_amount}}`, `{{state}}`, `{{case_name}}`: random entry from `caseglide-platform/src/data/nuclear-verdicts.ts` not in `used_verdict_ids` (last 30 days)
- `{{article_url}}`, `{{article_title}}`, `{{article_hook}}`: first entry in `caseglide-platform/src/data/newsletter-articles.ts` array (most recently added). `{{article_hook}}` = first paragraph of first content block.
- `{{proof_point}}`: hardcoded rotation in template file (25% defense spend / 10% settlement / 25% litigation volume)
- Apollo campaign metrics: `GET /v1/emailer_campaigns/{campaign_id}` at post time

**Templates (6 files, Wes approves once):**
1. `data-point.md` — `{{verdict_amount}}` verdict in `{{state}}` + question
2. `article-teaser.md` — `{{article_hook}}` + `{{article_url}}`
3. `client-outcome.md` — `{{proof_point}}` proof point + CaseGlide attribution
4. `industry-observation.md` — static text (Wes writes once), litigation trend + CaseGlide angle
5. `verdict-case-study.md` — `{{case_name}}`, `{{verdict_amount}}`, `{{state}}`, implications
6. `myth-misconception.md` — static text (Wes writes once), common belief + counter-data

**Approval gate:** Wes approves the 6 template files once. Structure is fixed; only variables change.

---

### Channel 2: Apollo — Autonomous List Building + One-Tap Activation

**Current state:** COS reports on campaign metrics. List building is manual or semi-manual. Campaign activation requires UI login.

**Apollo API capability confirmation:** Existing `scripts/apollo_campaign_manager.py` and `.claude/rules/apollo-operations.md` confirm the API supports: `contacts/search` (paginated, 300 req/min), `emailer_campaigns/{id}/add_contact_ids` (batches of 100), and sequence management. All Channel 2 operations are API-supported.

**Weekly list build (every Friday 10 AM, autonomous):**
1. `marketing-agent` queries Apollo `contacts/search` using pre-approved criteria from `campaign-criteria.md` (see schema below)
2. Dedup key: **email address**. For each result, check existence via `contacts/search?q_keywords={email}&page=1` against Apollo CRM (Apollo IS the CRM — no cross-system check needed). Skip contacts already found in CRM.
3. Additionally exclude: contacts already in any active sequence (checked via `emailer_campaigns/{id}/contact_ids`), bounced contacts (email_status = bounced)
4. Segment results into Campaign 1 batch (GC/CLO/VP Legal/Litigation Manager titles) and Campaign 2 batch (CRO/VP Risk/VP Claims/CCO titles)
5. Email Wes approval request: `1. Load 412 GC/CLO into Campaign 1? (Y/N)  2. Load 287 CRO/VP Risk into Campaign 2? (Y/N)`
6. On Y reply: runs `apollo_campaign_manager.py add-contacts` for approved batches, confirms via follow-up email

**Rate limit compliance:** 400 API calls/hour for sequence adds, 0.2s sleep between contact search pages, exponential backoff on 429.

**`campaign-criteria.md` schema** (file must exist before task can run — see Dependencies):
```yaml
campaign_1:
  titles: ["General Counsel", "CLO", "VP Legal", "Litigation Manager", "Deputy GC"]
  industries: ["Insurance", "Financial Services", "Healthcare"]
  min_employees: 500
  email_status: verified
  excluded_titles: []

campaign_2:
  titles: ["CRO", "VP Risk", "VP Claims", "CCO", "Chief Risk Officer", "Chief Claims Officer"]
  industries: ["Insurance", "Financial Services", "Healthcare"]
  min_employees: 500
  email_status: verified
  excluded_titles: []
```

---

### Channel 3: Newsletter — Beehiiv + Apollo Distribution

**Current state:** Beehiiv only, 9 subscribers. No distribution to other lists.

**HubSpot status:** Pre-2025 database, needs one-time audit before any contacts are usable. Not in active distribution until audit complete (see Legacy List Audit below).

**New model:**
- Cadence: every 2 weeks Tuesday 9 AM, fully autonomous
- Content generated from approved 3-part template (`newsletter-template.md`):
  - Variable `{{data_point}}`: one nuclear verdict stat or case pulled from `/src/data/`
  - Variable `{{article_url}}` + `{{article_title}}`: most recent article on LitigationSentinel.com
  - Fixed CTA: "Subscribe to Litigation Sentinel" + "Book Executive Briefing"
- Distribution (two separate systems — no contact crossover):
  - **Beehiiv:** send to existing Beehiiv subscriber list via `POST /v1/publications/{id}/broadcasts` (Beehiiv API, existing key). Beehiiv manages its own subscriber list — no contact push needed.
  - **Apollo:** send to Apollo CRM contacts NOT already enrolled in Campaign 1 or Campaign 2 sequences. COS loads eligible contacts into a dedicated Apollo "Newsletter" sequence (to be created, separate from Campaign 1/2 sequences). Sends via Sarah Johnson persona (mailbox ID: 69a598bdfd80760021e01e93). Apollo sequences handle send timing autonomously once contacts are loaded.
- These are independent distribution paths. A contact can be in both Beehiiv (as subscriber) and Apollo (as newsletter sequence contact) without conflict.
- Deliverability: Apollo sends use existing warm trycaseglide.com domain. All sends within approved infrastructure.

**Approval gate:** Wes approves `newsletter-template.md` once. COS fills variables and distributes on cadence.

---

### Channel 4: Legacy List Audit (One-Time)

**Sources:**
1. **HubSpot** — pre-2025 sales database. Unknown contact quality. Requires: export all contacts, filter by title match (same criteria as Campaign 1/2), check for email validity, dedup against Apollo CRM.
2. **Desktop spreadsheets** — handcrafted lists on Wes's Desktop. Requires: scan `~/Desktop` for `.csv`, `.xlsx` files, inspect headers for name/email/title/company columns, extract matching contacts, validate emails.

**Process (one session, delegated to marketing-agent):**
1. Export HubSpot contacts via HubSpot API or CSV export
2. Scan Desktop for spreadsheet files
3. For each source: filter by title + company size criteria, validate email format, dedup against Apollo CRM
4. Produce audit report: `tasks/legacy-list-audit.md` with counts per source and sample contacts
5. Email Wes: "Found X qualified contacts across HubSpot + Y spreadsheets. Load into Apollo? (Y/N)"
6. On Y: load approved contacts into Apollo CRM, add to appropriate campaign sequence

**This is a one-time task, not recurring.**

---

## Subagent Restructure

### `marketing-agent` (Expanded)

**Owns (metrics):**
- Contacts added to sequences per week (target: 400-500)
- LinkedIn posts published per week (target: 3)
- Newsletter sends executed per cadence (target: 1 per 2 weeks)

**New responsibilities:**
- Weekly autonomous list build (Friday) via Apollo API
- LinkedIn post generation from template variables + Buffer API scheduling
- Newsletter content generation + Beehiiv + Apollo distribution
- Legacy list audit (one-time)
- Campaign performance reporting (escalates only if bounce rate >5% or open rate drops >20% week-over-week)

**Removed:** Any task requiring Chrome. Any task producing a report without taking action.

---

### `sales-agent` (Refocused)

**Owns (metric):**
- Days-since-last-touch on every active deal (target: never >3 days)

**New behavior:**
- Monitors active deals daily via Pipedrive API (`GET /v1/deals?status=open`)
- Last-touch timestamp tracked via Pipedrive activity log (`GET /v1/deals/{id}/activities`)
- If any deal exceeds 3 days since last logged activity: drafts follow-up email, updates Pipedrive activity log, emails Wes draft for send approval
- Does not wait to be asked. Does not produce a report. Acts.

**Removed:** Waiting for Wes to notice deals going dark.

---

### `litigationsentinel-agent` (Unchanged scope, tighter trigger)

**Owns:** Platform uptime + deploy success rate

**Trigger:** On demand only — invoked by marketing-agent when article needs publishing, or by COS when platform issue flagged. Not scheduled.

---

### COS (Circuit Breaker Role)

**Session start:** Read `tasks/daily-digest.md` → run diagnosis → act

**`daily-digest.md` schema** (written by `morning-ops-brief` scheduled task):
```
## Date: YYYY-MM-DD
## Campaign Metrics
- Apollo Campaign 1: X delivered, X% open, X% bounce
- Apollo Campaign 2: X delivered, X% open, X% bounce
- Beehiiv subscribers: X

## Deal Status
- [Deal name]: last touch [date], [X] days ago, stage: [stage]
- ...

## Pending Approvals
- [Any Y/N decisions awaiting reply]

## Flags
- [Any metric exceeding threshold — bounce >5%, deal >3 days, open rate drop >20%]
```

**Escalates to Wes only when:**
- A metric is red (subagent missed its number 2 weeks in a row)
- A decision exceeds agent authority (strategic pivot, spend >$500, legal commitment)
- An active deal requires Wes's voice (demo invite, RFP submission, contract review)

**Does not escalate:** Routine approvals, content drafts, list sizes, platform deploys

---

## Scheduled Task Restructure

### Tasks to Kill
| Task | Reason |
|------|--------|
| `noon-chrome-scan` | Browser-dependent, replaced by API equivalents |
| `platform-health-check` | Rolled into `morning-ops-brief` API check |
| `state-file-integrity` | Replaced by outcome-based metrics in digest |

### Tasks to Rebuild
| Task | New Behavior |
|------|-------------|
| `morning-ops-brief` | Reads Apollo API + Beehiiv API + Pipedrive API. Writes `tasks/daily-digest.md`. Emails Wes 0-3 binary decisions if any pending. |
| `campaign-monitor` | Apollo API + Beehiiv API metrics only. Escalates to Wes if bounce >5% or open rate drops >20% WoW. Otherwise silent. |
| `deal-pipeline-watchdog` | Pipedrive API. Drafts follow-up + emails Wes for send approval if any deal >3 days since last activity. |

### New Tasks
| Task | Schedule | Behavior |
|------|----------|---------|
| `weekly-list-build` | Friday 10 AM | Apollo list build + dedup + email approval request to Wes |
| `linkedin-scheduler` | Mon/Wed/Fri 7:30 AM | Fill template variables + publish via Buffer API |
| `newsletter-send` | Every 2 weeks Tue 9 AM | Fill newsletter template + send to Beehiiv + Apollo newsletter sequence |
| `legacy-list-audit` | One-time | HubSpot + Desktop spreadsheet audit → approval email → Apollo import |

---

## Dependencies (Ordered by Priority)

| # | Dependency | Blocker for | Action |
|---|-----------|-------------|--------|
| 1 | Remove jailbreak from `CLAUDE.md` lines 83-98 | All development | Do now |
| 2 | Microsoft 365 MCP email send validated | Approval loop | Test send + reply parsing end-to-end |
| 3 | Buffer account + API key | LinkedIn automation | Create account, connect LinkedIn, store key |
| 4 | Pipedrive API key + write access confirmed | `deal-pipeline-watchdog` | Verify key exists + test activity write |
| 5 | LinkedIn template library (6 files) | `linkedin-scheduler` | One session with Wes (~15 min) |
| 6 | `campaign-criteria.md` approved | `weekly-list-build` | One session with Wes (~5 min) |
| 7 | `newsletter-template.md` approved | `newsletter-send` | One session with Wes (~5 min) |
| 8 | Legacy list audit completed | Channel 3 expansion | One-time, COS-autonomous |

---

## Success Metrics (90-Day)

| Metric | Current | Target | By |
|--------|---------|--------|----|
| Wes time/day | 1-3 hours | ≤1 hour | April 1 |
| LinkedIn posts/week | 0-1 (inconsistent) | 3 (autonomous) | April 1 |
| Apollo contacts added/week | Manual | 400-500 (autonomous) | April 1 |
| Newsletter subscribers | 9 | 100 | April 1 |
| Executive Briefings/month | 0 | 3+ | April 1 |
| Days-since-last-touch (max) | Unknown | ≤3 days | April 1 |
| Browser-required tasks | ~8 | ≤2 | April 1 |
| Legacy contacts audited + loaded | 0 | 1 batch | One-time |
