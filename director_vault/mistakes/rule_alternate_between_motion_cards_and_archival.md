---
category: pacing_monotony
occurrences: 2
created_at: 2026-11-14T20:31:28.485951Z
last_updated: 2026-11-14T20:31:28.499889Z
context_topic: Project Azorian
---
# Mistake Rule: Alternate between motion cards and archival imagery every 2 beats

## Category & Frequency
- **Category:** `#pacing_monotony`
- **Occurrences Caught:** 2
- **Last Encountered Topic:** [[topics/project_azorian|Project Azorian]]

## Bad Pattern (Mistake Caught)
```json
{
  "beat_1": "motion_card",
  "beat_2": "motion_card"
}
```

## Corrected State (Optimal Heuristic)
```json
{
  "beat_1": "motion_card",
  "beat_2": "treated_image"
}
```

## Permanent Director Directive
> **Rule:** Alternate between motion cards and archival imagery every 2 beats
