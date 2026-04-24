# Phase 7: Marketing / Landing Site Implementation Plan — DRAFT

> **Status:** Skeleton. Will be expanded into a task list when Phase 6 closes.

**Goal:** A small Next.js + HeroUI brand site (`apps/web-marketing/`, port 3002) that demonstrates the project's brand-facing UI chops and deep-links to the ops console for the demo CTA. No authentication; statically generated where possible.

**Architecture:**
- New `apps/web-marketing/` Next.js 14 App Router, TypeScript, HeroUI, Tailwind.
- Routes: `/`, `/features`, `/pricing`, `/contact`, `/app` (deep-link redirect to `:3001`).
- The contact form writes a row to a small `inquiry_log` model exposed by the existing Django API — no real email integration.

**Provisional task list (to be sharpened):**
1. Scaffold + design system reuse from `apps/web-ops/`.
2. Hero + value-prop landing.
3. Features grid (three pillar cards).
4. Pricing tier placeholder + contact form.
5. Static SEO meta + sitemap.
6. Compose service wiring + docs close.

**Phase 7 DoD (sketch):**
- `:3002` serves the brand site under HeroUI; lighthouse perf > 90 on the home route.
- Contact form posts an inquiry row visible via the ops console SMS/inquiry log.
- Roadmap row flips to ✅.
