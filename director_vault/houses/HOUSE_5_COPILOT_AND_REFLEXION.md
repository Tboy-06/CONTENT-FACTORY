---
title: House 5 - Copilot & Reflexion
house: HOUSE_5_COPILOT_AND_REFLEXION
type: moc_house
target_quota: 20000
current_quota: 325
tags: [house-5, copilot, reflexion, self-healing, mistakes, second-brain]
---

# 🤖 HOUSE 5: Director Copilot & Reflexion Healing

Upstream: [[00_SECOND_BRAIN_INDEX]]

House 5 powers the interactive AI Director Chat Drawer (`DirectorChatDrawer.tsx`), action schema execution, and reinforcement learning from mistakes.

## 📊 Sub-Room Quota Allocation (4,000 records each)
| Sub-Room | Focus | Quota | Status |
|---|---|---|---|
| `director_chat_commands` | Natural language editing requests mapped to copilot actions | `64 / 4,000` | OPEN |
| `reflexion_mistake_fixes` | Ground-truth editorial corrections (bad state -> healed state) | `261 / 4,000` | OPEN |

## 🛠️ Valid Copilot Action Schemas
- `modify_timeline_beats`: Updates specific beat parameters (`beat_updates`).
- `recut_genre`: Re-renders entire video into new genre physics (`target_genre`).
- `slice_viral_shorts`: Extracts high-retention snippet into a standalone short.
- `clone_reference_style`: Clones pacing/style of uploaded reference video.
- `edit_uploaded_video`: Trims silences, grades footage, and burns kinetic subtitles.
