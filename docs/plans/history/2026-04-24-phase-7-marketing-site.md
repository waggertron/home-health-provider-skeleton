# Phase 7: Marketing / Landing Site Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

## Goal

A static-ish brand site at `apps/web-marketing/` (`:3002`) that demonstrates
brand-facing UI chops alongside the operational ones, deep-links to the ops
console at `/app`, and boots inside the same compose stack.

## Pragmatic scope

The original draft sketched four separate routes (`/`, `/features`,
`/pricing`, `/contact`) plus an inquiry-log API integration. For a portfolio
demo that's a lot of surface for low marginal value. Phase 7 ships a single
scrolling landing page (`/`) with hero, features grid, pricing, and contact
section as in-page anchors, plus an `/app` deep-link. The contact form is
inert — clicking submit shows a "Demo only" notice. No new Django models.

## Architecture

- New `apps/web-marketing/` Next.js 16 + React 19 + HeroUI 3 + Tailwind 4 app
  (mirror of the Phase 5 stack so dependency drift stays low).
- Static rendering throughout.
- Theme tweaked toward the brand (lighter than ops, prominent CTA), but uses
  the same HeroUI primitives.

## Task list

1. **T1 — Scaffold + landing page (one commit).** New `apps/web-marketing/`
   with the Phase 5 toolchain (package.json + tsconfig + next.config + tailwind
   CSS-import + vitest). Single `app/page.tsx` rendering hero, three-card
   features section, pricing-tier card, and contact section. Top nav with a
   "Open the demo" CTA pointing at `http://localhost:3001`. One vitest
   smoke that renders the page.
2. **T2 — Compose service + Dockerfile.** Multi-stage `apps/web-marketing/
   Dockerfile`; `web-marketing` service in `docker-compose.yml` on `:3002`;
   Makefile gains `verify-marketing`. Manual smoke: `make up`, GET
   http://localhost:3002 → 200.
3. **T3 — Docs close + plan to history.** README + architecture roadmap
   flip; project layout includes apps/web-marketing/; plan moves to
   docs/plans/history/.

## Out of scope

- Real contact form / inquiry log model.
- Per-route SEO + sitemap beyond the home `<head>` meta.
- A11y/lighthouse perf tuning beyond defaults.

## Verification

- `make verify-marketing` clean (typecheck + 1 vitest).
- `make up` brings web-marketing healthy on `:3002`.
- Roadmap row flips to ✅.
