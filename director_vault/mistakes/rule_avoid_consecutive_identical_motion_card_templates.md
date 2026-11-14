---
category: pacing_monotony
occurrences: 2
created_at: 2026-11-14T20:31:28.571233Z
last_updated: 2026-11-14T20:37:31.325658Z
context_topic: Glomar Explorer Salvage
---
# Mistake Rule: Avoid consecutive identical motion card templates ('stat_counter'); rotate to 'quote_box' to maintain visual velocity.

## Category & Frequency
- **Category:** `#pacing_monotony`
- **Occurrences Caught:** 2
- **Last Encountered Topic:** [[topics/glomar_explorer_salvage|Glomar Explorer Salvage]]

## Bad Pattern (Mistake Caught)
```json
{
  "beat_index": 1,
  "prev_template": "stat_counter",
  "curr_template": "stat_counter"
}
```

## Corrected State (Optimal Heuristic)
```json
{
  "beat_index": 1,
  "prev_template": "stat_counter",
  "new_template": "quote_box"
}
```

## Permanent Director Directive
> **Rule:** Avoid consecutive identical motion card templates ('stat_counter'); rotate to 'quote_box' to maintain visual velocity.
