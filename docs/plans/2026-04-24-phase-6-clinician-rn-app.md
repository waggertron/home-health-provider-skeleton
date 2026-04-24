# Phase 6: Clinician RN App (Expo) Implementation Plan — DRAFT

> **Status:** Skeleton. Will be expanded into a task list when Phase 5 closes.

**Goal:** A field clinician's Expo + TypeScript app that consumes the same REST API and WebSocket gateway used by the ops console (Phase 5). Surfaces the day's route in order, supports check-in / check-out, and posts GPS pings so the ops map updates in real time.

**Architecture:**
- New `apps/web-rn/` Expo SDK 52+ app (TypeScript). Runs inside compose via `npx expo start --host lan` so iOS/Android simulators on the host can reach the bundler.
- Reuses the API client + auth context + realtime hook abstractions from `apps/web-ops/` (most likely lifted into a tiny `apps/shared-fe/` package during T1).
- Background GPS pings (foreground-only on the demo; battery-friendly defer to a real implementation) → `POST /positions/`.

**Tech Stack additions:** `expo@52`, `expo-router`, `expo-location`, `react-native-maps`, `@tanstack/react-query`, `zustand` (lightweight client state), `vitest` + `@testing-library/react-native`.

**Provisional task list (to be sharpened):**
1. Expo scaffold + shared-fe extraction.
2. Login screen + token storage (`expo-secure-store`).
3. Today's route screen.
4. Visit detail + check-in / check-out actions.
5. GPS-ping background tick.
6. Map screen (own route + own current position).
7. Smoke test using Expo's web preview to keep CI doable.
8. Compose service wiring + docs close.

**Phase 6 DoD (sketch):**
- Clinician RN user can log in via Expo Go on a simulator and see today's route.
- Pressing **Check In** transitions the visit and the ops console map updates within ~1s.
- GPS pings flow into `clinician.position_updated` events visible to the ops map.
