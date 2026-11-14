---
category: typography_overflow
occurrences: 2
created_at: 2026-11-14T20:31:28.557788Z
last_updated: 2026-11-14T20:37:31.294005Z
context_topic: Glomar Explorer Salvage
---
# Mistake Rule: Headline text on 9:16 cards must not exceed 28 characters to avoid layout edge clipping.

## Category & Frequency
- **Category:** `#typography_overflow`
- **Occurrences Caught:** 2
- **Last Encountered Topic:** [[topics/glomar_explorer_salvage|Glomar Explorer Salvage]]

## Bad Pattern (Mistake Caught)
```json
{
  "beat_id": "beat_01",
  "headline": "MASSIVE EXTREMELY LONG HEADLINE THAT CLIPS 9:16 LAYOUT ENTIRELY",
  "length": 63
}
```

## Corrected State (Optimal Heuristic)
```json
{
  "beat_id": "beat_01",
  "healed_headline": "MASSIVE EXTREMELY LONG",
  "length": 22
}
```

## Permanent Director Directive
> **Rule:** Headline text on 9:16 cards must not exceed 28 characters to avoid layout edge clipping.
