# Credentials Registry — Location Tracking Only
*NEVER store actual secret values in this file or any .md file.*

| Service | Key Name | Storage Location | Last Verified |
|---------|----------|-----------------|---------------|
| Apollo | API Key ("Litigation Sentinel") | `caseglide-platform/.env.local` as `APOLLO_API_KEY` | Mar 2, 2026 |
| Apollo | API Key ("CaseGlide Master Key") | Apollo Settings > Integrations (ends in `huA`) | Feb 25, 2026 |
| Beehiiv | API Key | `caseglide-platform/.env.local` as `BEEHIIV_API_KEY` + Vercel env vars | Feb 24, 2026 |
| Beehiiv | Publication ID | `caseglide-platform/.env.local` as `BEEHIIV_PUBLICATION_ID` + Vercel env vars | Feb 24, 2026 |
| Vercel | Access Token | Vercel dashboard (org: case-glide) | Feb 24, 2026 |
| Resend | API Key | `caseglide-platform/.env.local` as `RESEND_API_KEY` + Vercel env vars | Mar 3, 2026 |
| Resend | Notification Email | `caseglide-platform/.env.local` as `NOTIFICATION_EMAIL` + Vercel env vars | Mar 3, 2026 |
| Resend | Notification CC | `caseglide-platform/.env.local` as `NOTIFICATION_CC` + Vercel env vars | Mar 3, 2026 |
| Gmail | OAuth credentials | `gmail-cleanup/credentials.json` + `gmail-cleanup/token.json` | Never expose |

## Protocol
1. When Wes provides ANY new credential: store in `.env.local` immediately, then Vercel env vars, then update this registry.
2. If a key is needed and not in `.env.local`, check this registry FIRST before asking Wes.
3. NEVER put actual key values in .md files, MEMORY.md, or git-tracked files.
