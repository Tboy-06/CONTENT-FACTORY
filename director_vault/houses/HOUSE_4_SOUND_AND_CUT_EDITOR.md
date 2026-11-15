---
title: House 4 - Sound & Cut Editor
house: HOUSE_4_SOUND_AND_CUT_EDITOR
type: moc_house
target_quota: 20000
current_quota: 383
tags: [house-4, sound-design, audio-mastering, cut-velocity, second-brain]
---

# 🔊 HOUSE 4: Sound Design & Cut Velocity

Upstream: [[00_SECOND_BRAIN_INDEX]]

House 4 rules sound design, voice isolation, dynamic ducking, and millisecond-accurate cut pacing.

## 📊 Sub-Room Quota Allocation (4,000 records each)
| Sub-Room | Focus | Quota | Status |
|---|---|---|---|
| `cut_velocity_cpm` | Cut velocity rhythms, J-cuts, L-cuts, and match cuts | `46 / 4,000` | OPEN |
| `multi_voice_archival` | Speaker panning, radio EQ bandpass, and voiceover layering | `272 / 4,000` | OPEN |

## 🎚️ Audio Mastering Standards
- **Dialogue Level:** Loudness-normalized to `-14.0 LUFS`.
- **Sidechain Ducking:** Music ducks `-16dB` whenever speech is present.
- **Valid SFX Enums:** `thud.wav`, `whoosh.wav`, `click.wav`, `none`.
- **Comedic Pause:** `0.3s` silence injected before twist beats via FFmpeg `adelay`.
