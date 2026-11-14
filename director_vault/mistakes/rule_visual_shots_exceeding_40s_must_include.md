---
category: sluggish_retention
occurrences: 2
created_at: 2026-11-14T20:31:28.621823Z
last_updated: 2026-11-14T20:37:31.344444Z
context_topic: Glomar Explorer Salvage
---
# Mistake Rule: Visual shots exceeding 4.0s must include active 3D camera movements (orbital/dolly) to sustain attention.

## Category & Frequency
- **Category:** `#sluggish_retention`
- **Occurrences Caught:** 2
- **Last Encountered Topic:** [[topics/glomar_explorer_salvage|Glomar Explorer Salvage]]

## Bad Pattern (Mistake Caught)
```json
{
  "beat_id": "beat_03",
  "duration": 5.2,
  "camera_movement": null
}
```

## Corrected State (Optimal Heuristic)
```json
{
  "beat_id": "beat_03",
  "duration": 5.2,
  "camera_movement": "orbital"
}
```

## Permanent Director Directive
> **Rule:** Visual shots exceeding 4.0s must include active 3D camera movements (orbital/dolly) to sustain attention.
