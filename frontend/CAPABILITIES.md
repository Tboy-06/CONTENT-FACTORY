# Agent Capabilities (Frontend View)

Based on inspecting `backend/api` and `backend/agents`:

The UI requires knowing which stages work offline, which require network, and which are premium.

**Missing from Backend:**
- There is currently no API endpoint to fetch agent capabilities. `GET /api/workflow/spec` exists but returns empty data `{"workflow": {"nodes": [], "edges": []}}`.
- The frontend currently cannot "drive the UI from backend data" for capabilities because the backend does not report them.
- A health check endpoint for connectivity polling (`navigator.onLine` combined with a periodic check) is also missing from the API (no `/health` or `/api/health`).

To properly implement the offline/online/premium logic driven by the backend, the backend needs:
1. An endpoint like `GET /api/capabilities` (or populate `GET /api/workflow/spec`) that lists each stage and its supported modes (Offline/Local, Free/Network, Premium/Paid).
2. A fast `GET /api/health` endpoint for the connectivity checker.
