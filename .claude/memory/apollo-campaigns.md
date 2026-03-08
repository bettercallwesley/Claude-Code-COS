# Apollo Campaign Operations — Complete Process Guide

## Last Updated: March 2, 2026
## Author: CCO Post-Mortem from Campaign 1 Launch

---

## 1. CRITICAL CONCEPTS: People vs. Contacts

Apollo has two distinct entity types. Confusing them is the #1 source of campaign failures.

| | People | Contacts |
|---|---|---|
| **What** | Apollo's database of ~275M+ professionals | Records YOU own in your Apollo CRM |
| **API search** | `POST /v1/mixed_people/search` | `POST /v1/contacts/search` |
| **Cost to access** | 1 email credit per reveal | Free (already in your CRM) |
| **Add to sequence** | CANNOT directly — must save as contact first | YES via `add_contact_ids` |
| **Count in saved search** | Shows full universe (e.g., 59,556) | Only those already saved (e.g., 6,260) |

**ROOT CAUSE OF CAMPAIGN 1 DELAY:** The saved search showed 59,556 results. Only ~6,260 were actual CRM contacts. The remaining ~53K are "people" requiring credit-consuming conversion before sequencing.

---

## 2. COMPLETE WORKFLOW: Adding People to a Sequence

### Phase 1: Determine Contact Coverage
Before attempting to add anyone to a sequence, determine how many of your search results are already contacts.

```
POST https://api.apollo.io/v1/contacts/search
Body: {
  "api_key": "<key>",
  "page": 1,
  "per_page": 100,
  "person_titles": ["General Counsel", "Chief Legal Officer", ...],
  "person_locations": ["United States"],
  "contact_email_status": ["verified"]
}
```

Note the `pagination.total_entries` — this is how many contacts match your filters.

### Phase 2: Add Existing Contacts to Sequence
Use the `add_contact_ids` endpoint in batches.

```
POST https://api.apollo.io/v1/emailer_campaigns/{sequence_id}/add_contact_ids
Body: {
  "api_key": "<key>",
  "contact_ids": ["id1", "id2", ...],
  "emailer_campaign_id": "{sequence_id}",
  "send_email_from_email_account_id": "{mailbox_id}",
  "sequence_active_in_other_campaigns": true,
  "sequence_finished_in_other_campaigns": true,
  "sequence_no_email": false
}
```

**CRITICAL FLAGS — NEVER USE DEFAULTS:**

| Flag | Default | Set To | Why |
|------|---------|--------|-----|
| `sequence_active_in_other_campaigns` | `false` | `true` | Default silently skips contacts in ANY other active sequence |
| `sequence_finished_in_other_campaigns` | `false` | `true` | Default silently skips contacts who completed ANY other sequence |
| `sequence_no_email` | `false` | `false` | Set true only for phone-only sequences |

**Without setting both flags to `true`, you will add a tiny fraction of your contacts.**

### Phase 3: Save People as Contacts (Credit-Consuming)
For people who are NOT yet contacts:

**Option A: Bulk via UI** — Go to saved search > Select All > "Save to List" or "Add to CRM". 1 credit per email reveal.

**Option B: Via API** — `POST /v1/contacts` with `person_id` field. 1 credit per reveal.

**Option C: Bulk Enrich** — `POST /v1/people/bulk_match` with up to 10 person IDs per call.

---

## 3. RATE LIMITS

| Endpoint | Limit | Window | Strategy |
|----------|-------|--------|----------|
| `contacts/search` | ~300 requests | per minute | Paginate 100/page, sleep 0.2s |
| `add_contact_ids` | ~400 contacts | per hour | Batch 100/call, pause when approaching limit |
| `mixed_people/search` | ~300 requests | per minute | Same as contacts/search |

**CRITICAL:** `add_contact_ids` is per-hour, not per-minute. For 6,000+ contacts, expect ~15 hours.

---

## 4. THE UI POPUP PROBLEM ("Run quality checks")

Apollo "Proactive Recommendations" (Jan 2026). Upsell for Waterfall Enrichment.

**Does NOT work:** DOM removal (kills React state), DOM hiding, clicking Skip.
**DOES work:** API approach — bypass UI entirely with `add_contact_ids`.

**RULE: Always use the API for adding more than 100 contacts to a sequence.**

---

## 5. APOLLO UI GOTCHAS

- **"0 Total" in new layout:** Inactive sequences show contacts as "paused." Switch to "All" or "Paused" filter.
- **Quill.js editor:** `.ql-editor` class, innerHTML + input event dispatch works. Edits NOT saved until "Save changes" clicked.
- **Sequence activation via API doesn't work** — must use UI button click or JS `button.click()`.

---

## 6. CAMPAIGN STATE (Mar 2, 2026)

### Campaign 1 - GC / CLO Cold Outreach
- **Sequence ID:** `699deee1299e51000d383130`
- **URL:** `https://app.apollo.io/#/sequences/699deee1299e51000d383130`
- **Status:** ACTIVE (activated Mar 2, 2026)
- **Contacts loaded:** 7,833 active (fully loaded Mar 2)
- **Remaining CRM contacts:** 0 (all loaded)
- **People not yet contacts:** ~53K matching filters

### Sender
- **Mailbox:** Sarah Johnson <sarahjohnson@trycaseglide.com>
- **Mailbox ID:** `69a598bdfd80760021e01e93`

### Saved Search
- **Name:** "Master List - US Litigation Execs - Verified"
- **Total results:** 59,556 | CRM contacts: ~6,260
- **Filters:** 24 active

---

## 7. LAUNCH CHECKLIST

### Pre-Launch
- [ ] Sequence created with all email steps
- [ ] Email content finalized and "Save changes" clicked
- [ ] Sender mailbox connected and signature verified
- [ ] Schedule: Mon-Fri, 7AM-6PM ET
- [ ] Daily send limit configured (start 25/day, ramp to 50/day)
- [ ] Open + click tracking enabled
- [ ] Stop on reply, unsubscribe link present

### Contact Loading
1. `contacts/search` — count existing contacts
2. Run `apollo_campaign_manager.py add-contacts`
3. Monitor — ~400 contacts/hour
4. Verify in Apollo UI ("All" tab)

### Activation
1. Confirm contacts (check "Paused" if inactive)
2. Spot-check first 10 contacts
3. Activate via UI button (API activation doesn't work)
4. Monitor first 24 hours: bounce rate <5%

---

## 8. ERROR PATTERNS

| Error | Fix |
|-------|-----|
| `contacts_already_exists_in_current_campaign` | Skip |
| `in_other_active_campaign` | Set `sequence_active_in_other_campaigns: true` |
| `finished_other_campaign` | Set `sequence_finished_in_other_campaigns: true` |
| 429 | Backoff 60s, double each retry |
| 401 | Check API key |

---

## 9. POST-MORTEM LESSONS (Mar 2, 2026)

1. **Always API-first for bulk operations.**
2. **Check `contacts/search` count BEFORE assuming saved search = contacts.**
3. **Always set both override flags to `true`.**
4. **`add_contact_ids` rate limit is per-hour (~400/hr).**
5. **"0 contacts" in new layout != failure.** Check "Paused" tab.
6. **DOM manipulation of Apollo React UI is unreliable.**
7. **Sequence activation must be done via UI, not API.**
8. **The Python script is the canonical tool for bulk ops.**
