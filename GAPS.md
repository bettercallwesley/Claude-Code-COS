# GAPS.md — Known Gaps in Knowledge or Access
*No gap stays unaddressed for more than one session.*

## Ownership
- this should be maintained by you: CaseGlide's Chief of Claude Staff

| # | Gap | Impact | Resolution Status | Blocking? |
|---|-----|--------|-------------------|-----------|
| 1 | ~~Apollo FROM address~~ | ~~All outbound must send from new persona~~ | RESOLVED Mar 2 — sarahjohnson@trycaseglide.com connected, set as default, signature configured | NO |
| 2 | ~~Apollo sequence emails 2024 data~~ | ~~Emails referenced old data~~ | RESOLVED Mar 2 — all 5 emails have 2025 data (149 verdicts, $25.1B), sign-offs updated to Sarah | NO |
| 3 | EY regroup prep needed before 3/25 | Big 4 partnership opportunity — dossiers on Curcio, Kremer, Luciani needed | NOT STARTED — 23 days out, delegate to sales-agent week of 3/16 | NO |
| 4 | ~~LinkedIn profile URL~~ | ~~Needed for automated posting/commenting~~ | RESOLVED Mar 2 — `https://www.linkedin.com/in/wesley-todd-a9225929/` saved to MEMORY.md | NO |
| 5 | ~~Infrastructure files missing~~ | ~~5 files referenced in CLAUDE.md/MEMORY.md didn't exist on disk~~ | RESOLVED Mar 2 — all agent files, rules, REVENUE.md, credentials-registry.md created | NO |
| 6 | ~~InMail overdue follow-ups~~ | ~~Day 8/15 follow-ups overdue for multiple recipients~~ | REDESIGNED Mar 4 — manual sequence killed, 138 credits redeployed as single-touch high-priority messages. LGM evaluation at 30-day Apollo mark. | NO |
| 7 | ~~LinkedIn content calendar~~ | ~~Target 3 posts/week, no calendar built~~ | RESOLVED Mar 4 — 6 posts drafted for Mar 10-21. Wes approved. Posting starts Mar 10. | NO |
| 8 | ~~CRO/VP Risk sequence (Campaign 2)~~ | ~~Second campaign not yet built in Apollo~~ | RESOLVED Mar 7 — 5-step sequence BUILT, 3,735 contacts LOADED (162 skipped, 0 errors). Target activation Mar 17 via UI. | NO |
| 9 | ~~LitigationSentinel.com domain~~ | ~~Need to confirm domain purchased and pointed to Vercel~~ | RESOLVED — confirmed live, browser-tested Mar 2 | NO |
| 10 | ~~Campaign 1 bounce monitoring~~ | ~~First 24 hours critical, need <5% bounce rate~~ | RESOLVED Mar 4 — 0.07% bounce rate (5 of 207 delivered). Well below 5% threshold. | NO |
| 11 | ~~SageSure red items~~ | ~~No engineering owner assigned for red items in RFP~~ | RESOLVED Mar 4 — RFP v3 FINAL submitted (90% core). Deal advanced to demo scheduling phase. Champion: Desiree Ingram. | NO |
| 12 | ~~Hartford demo date~~ | ~~Not confirmed, demo package in progress~~ | RESOLVED Mar 4 — demo happened Feb 25. All 5 attendees identified. Follow-up email drafted in Outlook. | NO |
| 15 | ~~Beehiiv env vars missing from Vercel~~ | ~~Newsletter subscriptions silently failing~~ | RESOLVED Mar 4 — BEEHIIV_API_KEY updated with new Production key, BEEHIIV_PUBLICATION_ID confirmed correct. Redeployed to Vercel. | NO |
| 16 | ~~Notification system not deployed~~ | ~~Subscribe notifications + track-event route built but not on production~~ | RESOLVED Mar 4 — notification system was already deployed in commit bea9801 ("Add notification system"). Redeployed with correct Beehiiv key. | NO |
| 17 | Newsletter first email issue | First Litigation Sentinel email needed in ~2 weeks | NOT STARTED — marketing-agent to draft content | NO |
| 18 | ~~Resend DNS records for litigationsentinel.com~~ | ~~Notification emails sending from onboarding@resend.dev~~ | RESOLVED Mar 6 — DKIM + SPF verified, domain fully propagated. Resend package not installed in codebase (was removed during email flood fix). Re-add Resend send call when needed. | NO |
| 20 | **Hiscox Intent to Bid — DUE WED MAR 11** | Must submit intent to bid or lose RFP opportunity | Draft response complete, Wes must submit intent via iValua portal or email Sroop Grewal | **YES — DEADLINE** |
| 21 | Hiscox RFP pricing | Cannot submit final response without pricing (P1-P5 + day rates) | Wes must provide pricing inputs — see Hiscox_RFP_Questions_for_Wes.md | YES |
| 22 | Hiscox reference customers | RFP requires 2 reference customers willing to do calls | Recommend FIGA + PURE — Wes must confirm willingness | NO |
| 23 | Hiscox MSA/SOW legal review | MSA template with AI clauses requires attorney review | Wes must review as CEO/attorney — docs in Hiscox RFP Docs folder | NO |
| 24 | Hiscox policy documents | Ethics policy, BCP/DR doc, H&S policy requested — CaseGlide may not have formal versions | COS can draft if Wes approves — see Hiscox_RFP_Questions_for_Wes.md items 6-8 | NO |
| 19 | ~~Pipedrive deal creation process~~ | ~~Pacific Specialty needs adding~~ | RESOLVED Mar 5 — Pacific Specialty deal created in Pipedrive (Discovery stage, New Logo pipeline, Anisha Basi contact). Process: contact person + org + title + pipeline stage + save. | NO |
| 13 | ~~Campaign funnel conversion broken~~ | ~~7,833 Apollo contacts could consume all content with zero capture~~ | RESOLVED Mar 2 — /api/briefing-capture, email gate, ScheduleModal wired, program selection capture, CaseGlide.com links added | NO |
| 14 | ~~Resend API key needed~~ | ~~/api/briefing-capture requires RESEND_API_KEY env var~~ | RESOLVED Mar 3 — RESEND_API_KEY, NOTIFICATION_EMAIL, NOTIFICATION_CC added to .env.local + Vercel env vars, redeployed | NO |
