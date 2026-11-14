---
category: typography_overflow
occurrences: 1
created_at: 2026-11-14T20:37:31.312812Z
last_updated: 2026-11-14T20:37:31.312812Z
context_topic: Glomar Explorer Salvage
---
# Mistake Rule: Card highlight badges must not exceed 35 characters to fit high-contrast pill geometry.

## Category & Frequency
- **Category:** `#typography_overflow`
- **Occurrences Caught:** 1
- **Last Encountered Topic:** [[topics/glomar_explorer_salvage|Glomar Explorer Salvage]]

## Bad Pattern (Mistake Caught)
```json
{
  "beat_id": "beat_01",
  "highlight": "EXPONENTIAL 10X GROWTH IN REVENUE METRICS",
  "length": 41
}
```

## Corrected State (Optimal Heuristic)
```json
{
  "beat_id": "beat_01",
  "healed_highlight": "EXPONENTIAL 10X GROWTH IN",
  "length": 25
}
```

## Permanent Director Directive
> **Rule:** Card highlight badges must not exceed 35 characters to fit high-contrast pill geometry.
