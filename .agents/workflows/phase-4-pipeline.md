---
description: Phase 4. Pipeline board and History tab
---
1. Board tab with columns Queued, Researching, Writing, Storyboard, QC1 approval. The QC1 column is highlighted amber because the pipeline stops there and waits for the user. Cards show thumbnail (or placeholder), title, meta, progress.
2. History tab: table of job, state, duration, cost.
3. Live status through SSE if the backend supports it, otherwise polling with backoff that pauses when the tab is hidden and cancels on unmount.
4. A job in QC1 opens the approval screen (Phase 5 route).
5. Verify with the real backend: create a job, watch it move columns without refreshing, unplug the backend and confirm the UI shows an error state instead of hanging. Screenshot. Typecheck and build.
6. Stop and report.

Also in this phase (before the stop):
- Engine badge (Premium/Free/Local) on every card and History row.
- Show a "Waiting for a connection" state for jobs or actions that need network. Verify by going offline mid-job.
