# PLATFORM.md — Platform State
*Updated: 2026-03-03*

## Repo
github.com/bettercallwesley/litigation-sentinel
Stack: Next.js 14, TypeScript, Tailwind CSS, Framer Motion
Deployment: Vercel — commits to main auto-deploy (~60 seconds)
Live: www.litigationsentinel.com (purchased, connected Feb 24)
Fallback: litigation-sentinel.vercel.app
OG metadata: live on all routes

## Routes
| Route | Status | Notes |
|-------|--------|-------|
| / | ✅ Live | Editorial home, 2 articles featured |
| /briefing | ✅ Live | 6-question assessment |
| /council | ✅ Live | 12-week program |
| /trial | ✅ Live | 30-day portfolio dashboard |
| /article/[slug] | ✅ Built | Full article pages |

## Analytics & Tracking
| Item | Status |
|------|--------|
| GA4 | ✅ Added |
| Apollo custom tracking domain (track.trycaseglide.com) | ✅ DNS configured Mar 3 |
| LinkedIn Insight Tag | ✅ Added |
| Beehiiv subscribe | ✅ Wired |
| /api/briefing-capture → Resend email + Beehiiv | ✅ Built |
| ScheduleModal form submission | ✅ Wired (briefing, council, trial) |
| Assessment results email gate | ✅ Built |
| Program selection capture (Council/Trial) | ✅ Built |
| CaseGlide.com link in SentinelFooter | ✅ Added |

## Published Articles
| Title | Word Count | Published |
|-------|-----------|-----------|
| "Litigation Management Is Dead. What Replaces It Is Already Here." | ~2,200 | Feb 2026 |
| "Your Quarterly Attorney Report Is Lying to You" | ~1,550 | Feb 2026 |

## Article Build Queue
| Article | Status |
|---------|--------|
| "Nuclear Verdicts Are Up 28%..." | 🔲 Body needed |
| Counsel performance piece | 🔲 Outline needed |
| Jurisdiction / judicial hellholes deep dive | 🔲 Not started |

## Deployment Log
| Date | Change | Result |
|------|--------|--------|
| Feb 24, 2026 | Domain purchased, connected to Vercel | ✅ Live |
| Feb 24, 2026 | OG metadata added all routes | ✅ Live |
| Feb 2026 | 2 articles published | ✅ Live |
| Mar 2026 | GA4, Insight Tag, Beehiiv, Request Briefing form, /article/[slug] | ✅ Complete |
| Mar 2, 2026 | Campaign funnel repair: /api/briefing-capture, ScheduleModal wired, email gate on results, program selection capture, Council/Trial schedule buttons, CaseGlide.com footer links | ✅ Built, pending deploy |
| Mar 3, 2026 | Apollo custom tracking domain: CNAME track.trycaseglide.com → victorious-crab.aploconnect.com added to Squarespace DNS | ✅ DNS saved, propagation ~4 hrs |

## Deployment Flow (Wes does this in 10 seconds)
Chief of Staff writes code → tells Wes:
"Open a new issue at github.com/bettercallwesley/litigation-sentinel,
title: [X], body: @claude implement this: [exact spec]"
→ GitHub Action runs → Vercel deploys → done

## Design Rules
- Headings: Source Serif 4 | Body: DM Sans | Never: Inter, Roboto, system fonts
- Mobile-responsive at 700px
- "Liana Rodriguez" (not Martinez) | "Case Clerk AI" (not Clerk.ai)
