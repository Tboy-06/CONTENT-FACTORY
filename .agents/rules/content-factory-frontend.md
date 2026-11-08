---
trigger: always_on
description: Content Factory frontend rebuild rules (design system, backend contract, scope limits)
---

# Content Factory frontend rebuild

Stack: React + TypeScript + Vite in frontend/. Backend: Python FastAPI on port 8000.

## Visual reference (read before building any screen)
- frontend/design/board-2.png is the main look. board-3.png is a richer variant, use it only for the elements listed below. board-1.png is an older draft.
- frontend/design/reference.html is a clickable prototype. Open it in the browser and copy layout, spacing, colors, interactions. Read its CSS for exact values.
- Boards are AI-generated, so small text is unreliable. If board and reference.html disagree, reference.html wins.

## Design system
- Background #0b0e17. Glass cards: rgba(255,255,255,0.045) fill, 1px rgba(255,255,255,0.1) border, backdrop blur.
- Accent gradient #4f7cff to #8b5cff. Success #3ecf8e, warning #f5b84a, danger #ff6b7a, muted text #97a0b8. Font: Inter.
- All colors, radii, spacing live in one tokens file as CSS variables. No hardcoded hex in components.
- Sidebar is fixed and docked, never floating. Clicking the brand collapses it to a ~68px icon rail. Persist the state.
- Top bar on every screen: search, an Online/Offline pill, paid-spend chip ("Paid spend $18.40 of $50 cap" with a small bar), avatar.
- Every screen has loading, empty and error states.
- Sidebar has exactly six items: Dashboard, Create, Pipeline, Vault, Agents, Settings.

## Backend contract
- frontend/server.ts only proxies /api/* to port 8000. No Express logic. No mocked endpoints. No fake data.
- Before writing API code, read backend/api/*.py and list the real endpoints and response shapes. Never invent endpoints.
- Known: POST /api/jobs/score-niche, POST /api/jobs/{job_id}/approve, POST /api/jobs/{job_id}/reject, the settings API.
- Spend tracking: if the backend does not record per-job cost or monthly totals, show "unavailable" in the UI and list the missing endpoints in your report. Never fabricate numbers.
- All fetches go through one typed client at src/api/client.ts, with React Query for server state.
- Job status: use SSE if the backend supports it. Otherwise poll with backoff, pause when the tab is hidden, cancel on unmount. The UI must never hang on a failed request.

## Offline and online, free and paid
The app must work in all of these situations. They are two separate axes: connectivity (online or offline) and engine tier (Free or Premium, chosen per job).
- Offline means no network. Premium engines need network, so Premium is paused offline. The Premium option is disabled with a reason, and the job runs on local engines or waits in a queue (the user chooses).
- Free engines use local tools and free-tier services. Free jobs cost $0.00 and never count toward the monthly spend cap. Estimated cost shows $0.00 for Free.
- Do NOT hardcode which stages work offline. Read backend/agents/* and the config, find which agents have a local path (for example local transcription, FFmpeg) and which need network, and write the result to frontend/CAPABILITIES.md. Drive the UI from backend data. If the backend cannot report capabilities, list what is missing instead of guessing.
- Connectivity: src/lib/connectivity.ts combines navigator.onLine with a periodic backend health check (use an existing health endpoint if there is one, otherwise report that one is needed). The user can also force Offline mode in Settings.
- Offline UI: Offline pill in the top bar, an amber banner under it, Premium disabled, a "Waiting for a connection" state for anything that needs network (publishing, URL ingest, web research). Nothing may fail silently.
- Pipeline cards and History rows show an engine badge: Premium, Free or Local. Vault shows "Free, local engines" or the dollar cost per video.
- Settings has a Connection and engines card: Offline mode switch, queue publishing while offline switch, connection status.
- reference.html has an Online/Offline pill in the top bar. Click it to see the offline behaviour. Match it.

## Extra elements to adopt from board-3.png (not in reference.html yet)
- QC1 screen: a red banner at the top, "Rendering is blocked until you approve this storyboard".
- Copilot Job configuration: when a premium asset is selected, show a live cost delta row (for example "Premium asset selected, +$0.30" and the new total). Never show it offline.
- Dashboard: a compact "Current production" stage tracker for the active job (Researcher, Scriptwriter, Storyboard, Generation, Assembly, Render). Keep the rest of the Dashboard thin.
- Vault: a detail side panel for the selected video with script excerpt, tags, cost, Download and Share.
- Pipeline cards: cost and elapsed time on each card.
- Settings: default model and fallback model, notification preferences.
- Agents (Phase 9 only): cost per run on each card, and an inspector panel with a Test agent button.
Do NOT adopt from board-3.png: the Remix / Spin tiles, Workflow Canvas, Calendar, Executions screen (job logs go in a drawer on the Pipeline History tab), the "Pro Plan" label, "New Agent", and any image-model that has no official API (check before listing one).

## Do not build
- Workflow Canvas, Telegram Simulator, Calendar view, a separate Executions screen (Pipeline has a History tab), a separate Copilot sidebar item, credits, plan or Premium account badges.
- Any "Remix", "Remix and Spin", or copyright-evasion feature. Not in the UI, not in the backend, not as a tile or stub. Remove any existing frontend code for it. Do not process other people's videos to evade detection.

## Working style
- One phase per conversation. Finish and verify the phase, then stop and report. Do not start the next phase.
- Follow verify_work.md (two-stage, reverse-order verification).
- Use the browser subagent to open the running frontend and exercise the real flow. Capture screenshots and compare against reference.html.
- Typecheck and production build must pass with zero errors before you call a phase done.
- Report what you actually observed, not what the code suggests. End every phase with a list of anything that does not work or needs a backend change.
