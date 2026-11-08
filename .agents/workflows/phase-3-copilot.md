---
description: Phase 3. Copilot and Job configuration
---
1. Build chat on the left and the Job configuration panel on the right.
2. Basic/Advanced toggle. Basic: format, duration, platform, engine (Free/Premium). Advanced: voice, visual style, reference mode (with a reference URL field for Clone a Video, structure and pacing only), quality, spend cap for this job.
3. Show the niche score (GO or AVOID) from POST /api/jobs/score-niche and an estimated cost. If cost is unavailable from the backend, say so in the UI.
4. "Generate plan" creates a real job through the API and routes to Pipeline.
5. Verify with the real backend: enter a niche, see the real score, create a job, see it appear. Screenshot. Typecheck and build.
6. Stop and report.

Also in this phase (before the stop):
- Engine toggle (Free/Premium). Offline, Premium is disabled with a reason and the estimate shows $0.00. Online Free also shows $0.00.
- Advanced shows a stage-engine table built from CAPABILITIES.md and backend data, not hardcoded values.
- If offline, "Generate plan" offers: run on local engines now, or queue until online.
