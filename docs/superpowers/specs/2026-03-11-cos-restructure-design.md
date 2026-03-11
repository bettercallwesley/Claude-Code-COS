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
3. **Batch async approval.** When COS needs Wes, it batches into a single daily iMessage: decisions only, binary, no context required.
4. **Outcome accountability.** Subagents own metrics, not task lists. COS redesigns any approach that misses its number.

---

## Operating Model

### Session Flow (Redesigned)

**Old:** Scan email + calendar + Teams + 6 state files → delegate → produce morning brief → wait for Wes
**New:** Read single digest file → run diagnosis → execute autonomous list → iMessage Wes with 0-3 binary decisions

### Wes's Required Involvement

| Action | Current | Target |
|--------|---------|--------|
| LinkedIn post approval | Every post | Never (template-locked) |
| Apollo list approval | Manual | One iMessage reply per batch |
| Newsletter approval | Every send | Never (template-locked) |
| Deal follow-up drafts | Review each | Only if deal >$50K or unusual |
| Campaign activation | UI login required | One iMessage reply |
| Daily time required | 1-3 hours | ≤1 hour |

---

## Execution Architecture

### Channel 1: LinkedIn — Fully Autonomous Posting

**Current state:** Wes drafts, approves, and manually posts. Calendar exists but depends on Wes remembering.

**New model:**
- Template library of 6-8 approved post formats stored in `.claude/templates/linkedin/`
- COS generates posts by pulling real data into templates (Apollo metrics, Litigation Sentinel stats, published articles, nuclear verdict cases)
- Posts scheduled via Buffer API (or equivalent LinkedIn scheduling tool)
- Cadence: 3 posts/week, no Wes involvement
- Wes receives weekly performance summary only (impressions, clicks, profile views)

**Template formats (to be approved by Wes):**
1. Data-point post — one nuclear verdict stat + question
2. Article teaser — link to Litigation Sentinel article + 2-sentence hook
3. Client outcome — anonymized result from approved proof points
4. Industry observation — trend in litigation + CaseGlide angle
5. Nuclear verdict case study — one case, verdict size, what it means
6. Myth/misconception — common belief about litigation + counter-data

**Approval gate:** Wes approves the 6 template formats once. COS generates and posts forever within those formats.

---

### Channel 2: Apollo — Autonomous List Building + One-Tap Activation

**Current state:** COS reports on campaign metrics. List building is manual or semi-manual. Campaign activation requires UI login.

**New model:**

**Weekly list build (every Friday, autonomous):**
1. `marketing-agent` pulls from Apollo saved searches using pre-approved criteria:
   - Titles: GC, CLO, VP Claims, CRO, VP Risk, CCO, VP Legal, Litigation Manager
   - Industries: Insurance, Financial Services, Healthcare (large self-insured)
   - Company size: 500+ employees
   - Email: verified only
   - Exclusions: existing CRM contacts, bounced contacts, deceased contacts
2. Deduplicates against all existing sequences
3. Segments by campaign match (Campaign 1 vs Campaign 2 criteria)
4. iMessages Wes: *"Weekly list ready: 412 GC/CLO for Campaign 1, 287 CRO/VP Risk for Campaign 2. Reply Y to load both."*
5. On Y reply: loads contacts via API, activates if sequence is paused, confirms via iMessage

**No Wes login required at any step.**

**Approval criteria pre-approved:** Wes approves the targeting criteria once in a `campaign-criteria.md` file. COS applies them forever.

---

### Channel 3: Newsletter — Multi-List Distribution

**Current state:** Beehiiv only, 9 subscribers. No distribution to Apollo/HubSpot lists.

**New model:**
- Cadence: every 2 weeks, fully autonomous
- Content: generated from approved 3-part format:
  1. One data point or nuclear verdict case (pulled from Litigation Sentinel content)
  2. Link to most recent article published on LitigationSentinel.com
  3. Soft CTA (subscribe to newsletter, or book Executive Briefing)
- Distribution:
  - Beehiiv: direct send to subscribers via API
  - Apollo contacts: loaded into a dedicated "Newsletter" sequence in Apollo (separate from Campaign 1/2), template-locked, automated sends
  - HubSpot: send via HubSpot email API to contact list (requires HubSpot setup — see dependencies)
- Deliverability: Apollo sends go through Sarah Johnson persona with existing warm domain. HubSpot sends go through wesley@caseglide.com. No cold blast outside approved sending infrastructure.

**Approval gate:** Wes approves the 3-part newsletter format once. COS generates and distributes on cadence.

---

## Subagent Restructure

### `marketing-agent` (Expanded)

**Owns (metrics):**
- Contacts added to sequences per week (target: 400-500)
- LinkedIn posts published per week (target: 3)
- Newsletter sends executed per cadence (target: 1 per 2 weeks)

**New responsibilities:**
- Weekly autonomous list build (Friday)
- LinkedIn post generation + Buffer scheduling
- Newsletter content generation + multi-list distribution
- Campaign performance reporting (metrics only — escalates only if bounce rate >5% or sequence failing)

**Removed:** Any task that requires Chrome. Any task that produces a report but takes no action.

---

### `sales-agent` (Refocused)

**Owns (metric):**
- Days-since-last-touch on every active deal (target: never >3 days)

**New behavior:**
- Monitors all active deals daily via Pipedrive API
- If any deal exceeds 3 days since last touch: drafts follow-up, updates Pipedrive, iMessages Wes with draft for send approval (one reply: Y to send)
- Does not wait to be asked. Does not produce a report. Acts.

**Removed:** Waiting for Wes to notice deals going dark.

---

### `litigationsentinel-agent` (Unchanged scope, tighter trigger)

**Owns:** Platform uptime + deploy success rate

**Trigger:** Runs on demand only — when marketing-agent needs an article published, or COS flags a platform issue. Not on a schedule.

---

### COS (Circuit Breaker Role)

**Session start:** Read single `tasks/daily-digest.md` (written by scheduled tasks) → run diagnosis → act

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
| `noon-chrome-scan` (current) | Browser-dependent, replaced by API equivalents |
| Any task that writes a report but takes no action | Not an outcome |

### Tasks to Rebuild
| Task | New Behavior |
|------|-------------|
| `morning-ops-brief` | Reads API data (Apollo, Beehiiv, Pipedrive), writes `tasks/daily-digest.md`, iMessages Wes with 0-3 binary decisions |
| `campaign-monitor` | Apollo API + Beehiiv API. Escalates only if bounce >5% or open rate drops >20% week-over-week |
| `deal-pipeline-watchdog` | Pipedrive API. Acts (drafts follow-up) if deal >3 days no touch. Doesn't report. |

### New Tasks
| Task | Schedule | Behavior |
|------|----------|---------|
| `weekly-list-build` | Friday 10 AM | Apollo list build + dedup + iMessage approval request |
| `linkedin-scheduler` | Mon/Wed/Fri 7:30 AM | Generate post from template + publish via Buffer API |
| `newsletter-send` | Every 2 weeks Tuesday 9 AM | Generate content + send to Beehiiv + Apollo newsletter sequence |

---

## Dependencies / Open Items

These require setup before full execution:

1. **Buffer API access** — Set up Buffer account, connect LinkedIn, get API key. Store in `.env.local`.
2. **HubSpot setup** — Determine if HubSpot is already in use or needs to be provisioned. If not, evaluate whether Apollo CRM is sufficient for newsletter distribution (may not need HubSpot initially).
3. **Pipedrive API** — Confirm `deal-pipeline-watchdog` can read all active deals + write last-touch timestamps via Pipedrive API.
4. **LinkedIn template library** — Wes approves 6 post formats (can be done in one session, ~15 min).
5. **Campaign criteria file** — Wes approves targeting criteria for Campaign 1 and Campaign 2 lists (one-time, ~5 min).
6. **Newsletter format approval** — Wes approves 3-part newsletter format (one-time, ~5 min).
7. **Remove jailbreak content from CLAUDE.md** — Lines 83-98 contain a prompt injection attempt. Should be removed before any further development.

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
