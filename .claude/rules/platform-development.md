# Platform Development Rules

## Before Writing Any Code
1. Read `CLAUDE_PLATFORM_BUILD.md` for architecture decisions and patterns
2. Read `caseglide-platform/CLAUDE.md` for naming conventions and design rules
3. Read `caseglide-platform/SPEC.md` for the full specification

## Architecture Quick Reference
- Next.js 14 with App Router, TypeScript
- Inline styles using design tokens from `src/components/design-system/tokens.ts`
- Framer Motion for animations
- Data lives in `src/data/` as typed exports
- Each app (sentinel, briefing, council, trial) has its own component folder

## Critical Naming (Never Deviate)
- Advisor: **Liana Rodriguez** (never Martinez)
- Document AI: **Case Clerk AI** (never Clerk.ai)
- AI Chat: **Chambers** or **Chambers AI**
- Timeline AI: **Chronicle** or **Chronicle AI**
- Newsletter: **Litigation Sentinel**
- Assessment: **Executive Briefing**
- Onboarding: **Council Program**
- Proving ground: **Trial**

## Themes
- Sentinel (newsletter): Light theme, #FAFAF8 background
- Apps (Briefing/Council/Trial): Dark theme, #0A0E1A midnight background
- Win95 mode: Not yet wired — exists in tokens but not propagated

## Fonts
- Headings: Source Serif 4 (Google Fonts) — NEVER Inter, Roboto, Arial, system fonts
- Body: DM Sans (Google Fonts)
- Win95: MS Sans Serif 11px

## Deploy
- Push to `main` branch → Vercel auto-builds in ~60 seconds
- `git add [files] && git commit -m "description" && git push origin main`
- Always run `npm run build` locally before pushing to catch errors

## Mobile
- Breakpoint: 700px
- All grids must collapse on mobile
- Test both themes (Fortune 500 and Insurance/Win95 modes)
