---
description: Phase 1. Shell, tokens, routing, API client, UI primitives
---
1. Read the rules file and open frontend/design/reference.html in the browser.
2. Read backend/api/*.py. Write the real endpoint list to frontend/API_NOTES.md.
3. Delete the old frontend components that the rules say not to build. Keep server.ts as the proxy only.
4. Build src/styles/tokens.css, the fixed collapsible sidebar (six items), the top bar with the spend chip, and routing for all six screens (empty placeholders are fine).
5. Build src/api/client.ts and the React Query setup.
6. Build UI primitives: Card, Button, Badge, Tabs, Modal, Progress, EmptyState.
7. Run typecheck and build. Open the app in the browser, collapse and expand the sidebar, click every nav item, screenshot the result next to reference.html.
8. Stop and report.

Also in this phase (before the stop):
- Read backend/agents/* and write frontend/CAPABILITIES.md: which stages can run locally, which need network, which are paid. Do not guess.
- Build src/lib/connectivity.ts, the Online/Offline pill, and the offline banner. Verify by turning the network off in the browser and by stopping the backend.
