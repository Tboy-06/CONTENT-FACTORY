---
description: Phase 5. Storyboard approval (QC1)
---
1. Build the approval screen: preview, scene thumbnails, tabs Script / Scenes / Visuals, narration, visual prompts, estimated cost with breakdown (narration, b-roll, render), a warning when a scene needs a premium asset.
2. Buttons: Reject, Edit, Approve and continue. Wire Approve and Reject to the real endpoints. Disable double submits.
3. Verify with the real backend: run a job to QC1, approve it, confirm it resumes and finishes. Run another and reject it, confirm the state. Screenshot each step. Typecheck and build.
4. Stop and report. This completes the core loop.

Also in this phase (before the stop):
- Cost estimate shows $0.00 for Free engines. When a scene needs a premium asset and the user is offline, show the fallback warning instead of the cost warning.
