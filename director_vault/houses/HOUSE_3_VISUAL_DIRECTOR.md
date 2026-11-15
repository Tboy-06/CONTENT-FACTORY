---
title: House 3 - Visual Director
house: HOUSE_3_VISUAL_DIRECTOR
type: moc_house
target_quota: 20000
current_quota: 404
tags: [house-3, visual-director, camera-moves, motion-cards, second-brain]
---

# 🎨 HOUSE 3: Visual Director & Camera Physics

Upstream: [[00_SECOND_BRAIN_INDEX]]

House 3 governs motion graphics, GLSL depth shaders, camera moves, and color grading filters.

## 📊 Sub-Room Quota Allocation (4,000 records each)
| Sub-Room | Focus | Quota | Status |
|---|---|---|---|
| `depth_3d_shaders` | Ray-marched OpenGL GLSL shaders & DepthFlow displacement | `25 / 4,000` | OPEN |
| `motion_hud_cards` | Pillow 60fps 2D cards (steppers, counters, declassified scans) | `15 / 4,000` | OPEN |
| `color_grade_lighting` | Ev1 color grading LUTs (teal_split, hard_bw, skit_warm, etc.) | `37 / 4,000` | OPEN |
| `broll_composition` | Pexels/archival shot framing, golden ratio, subject eye-lines | `309 / 4,000` | OPEN |

## ⚙️ Strict Engine Enums
- **Valid Cameras:** `cosine_in`, `cosine_out`, `snap_zoom`, `camera_shake`, `orbital`, `dolly_vertigo`, `rack_focus_bokeh`, `pan_right`
- **Valid Filters:** `teal_split`, `hard_bw`, `amber`, `skit_warm`, `action_crush`, `cinema_scope`
- **Valid Motion Types:** `treated_image`, `declassified_scan`, `evidence_board`, `map_flyover`, `stat_counter`, `red_slam_word`, `workflow_stepper`, `3_item_list`, `quote_box`
