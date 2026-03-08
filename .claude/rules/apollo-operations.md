# Apollo Operations Rules — Mandatory for All Campaign Work

## People vs. Contacts
- Apollo saved search counts show PEOPLE (full database). Only CONTACTS (your CRM) can be added to sequences.
- Always run `POST /v1/contacts/search` first to get actual CRM contact count before any sequence operation.
- Converting people to contacts costs 1 email credit each via `POST /v1/contacts` or bulk UI "Save to List."

## Sequence Contact Addition — API Only for Bulk
- NEVER use Apollo UI to add >100 contacts to a sequence. The "Run quality checks" popup blocks bulk UI operations.
- Use `POST /v1/emailer_campaigns/{id}/add_contact_ids` with batches of 100.
- MANDATORY FLAGS (defaults silently exclude most contacts):
  - `sequence_active_in_other_campaigns: true` (default false — skips contacts in any active sequence)
  - `sequence_finished_in_other_campaigns: true` (default false — skips contacts who finished any sequence)
  - `sequence_no_email: false`

## Rate Limits
- `add_contact_ids`: ~400 API CALLS/hour (not contacts). Track calls, not contact count.
- `contacts/search`: ~300 requests/minute. Paginate 100/page with 0.2s sleep.
- On 429: exponential backoff starting 60s, doubling, max 5 retries.

## Sequence Activation
- Apollo API does NOT support sequence activation. PUT/POST to update endpoints returns unchanged or 404.
- Must activate via UI button click or JavaScript `button.click()` on the Activate button element.

## Sender
- Current approved sender: Sarah Johnson <sarahjohnson@trycaseglide.com> (mailbox ID: 69a598bdfd80760021e01e93)
- Steve Kiernan mailboxes are PERMANENTLY DISABLED — never use.

## Script
- Canonical tool: `scripts/apollo_campaign_manager.py`
- Requires: `APOLLO_API_KEY` env var (stored in caseglide-platform/.env.local)
- Commands: `count-contacts`, `count-people`, `add-contacts --sequence-id --mailbox-id`

## Pre-Launch Checklist
1. Verify contact count via API (not saved search count)
2. Verify sender mailbox is connected and signature correct
3. Load contacts via script with both override flags set to true
4. Activate via UI (not API)
5. Monitor first 24 hours: target <5% bounce rate
