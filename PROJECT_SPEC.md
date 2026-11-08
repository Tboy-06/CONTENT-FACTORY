# CONTENT-FACTORY — Full Project Specification

**Last Updated:** 2026-08-31  
**Location:** `D:\CONTENT-FACTORY` (separate from RUTE project)

---

## 1. Concept

Your personal AI content company. You're the only human — you set goals and approve via Telegram; an agent team researches, writes, produces, and posts original videos to all your platforms, then learns from the numbers.

---

## 2. The 9 Agents & Functionalities

### 1. MANAGER (Chief of Staff)
- Receives your goals (e.g., "3 finance shorts/week") and breaks them into tasks
- Assigns work to agents, tracks every job's state, retries failures
- Wakes the pipeline on schedule; escalates to you on Telegram when stuck or awaiting approval
- Enforces the rulebook: nothing posts without passing QC + (optionally) your approval

### 2. RESEARCHER
- Scans your niches daily: trending topics, viral videos, rising formats
- Sources: YouTube search/data API, web scrape, Agent-Reach-style sources (Reddit, X, RSS, GitHub, LinkedIn, etc.)
- Scores each idea for virality potential; outputs a **research brief** (topic, angle, why it works, references)
- Maintains an idea bank so the pipeline never runs dry

### 3. STYLE ANALYST (The v7/v8 trick, automated)
- Watches reference videos with a vision model (Gemini)
- Extracts the **formula, not the content**: hook structure, pacing, scene rhythm, visual style guide, character design language
- Saves style guides to the vault for reuse — this keeps you copyright-safe

### 4. SCRIPTWRITER
- Combines research brief + style guide → writes **original** scripts: hooks, beats, captions, titles, hashtags
- Generates per-platform variants (TikTok punchy vs YouTube longer vs X thread)
- Produces 2–3 variants per topic; you pick or it auto-picks

### 5. ART DIRECTOR
- Turns scripts into character prompts + reference images (consistent characters across videos via a **character bible**)
- Generates scene-by-scene shot lists and image assets per scene
- Covers/thumbnails per platform

### 6. VIDEO EDITOR
- Assembles the final video: images/AI-clips + TTS voiceover + auto-captions + music + transitions
- **Free path** (default): AI images + Edge-TTS + FFmpeg motion/captions ≈ $0/video
- **Premium path**: Veo video gen (~$0.35–0.50/sec) — configurable per video
- Renders every aspect ratio: 9:16 (Shorts/Reels/TikTok), 16:9 (YouTube long-form), 1:1 (Instagram feed)

### 7. QUALITY CONTROL (The Bouncer)
- Reviews everything before it leaves the house: script originality, caption/audio sync, banned-word/policy risk, AI-disclosure tags, brand consistency
- Verdicts: PASS → poster, FAIL → back to the right agent with notes, UNCERTAIN → you decide on Telegram

### 8. POSTER
- Publishes/schedules to TikTok, Instagram, YouTube, Facebook, X, LinkedIn via **Postiz self-hosted (free)** or Blotato API
- Per-platform captions, hashtags, optimal-time scheduling
- Respects per-platform approval mode

### 9. ANALYST (The v10 knowledge, automated)
- Pulls analytics daily (views, retention, traffic sources, subs)
- Computes what's working: which hooks, topics, lengths, posting times
- Writes weekly report to Telegram + feeds learnings back into RESEARCHER's briefs — the loop that makes it get better over time

---

## 3. Shared Infrastructure

| Component | Description |
|---|---|
| **The Vault (Memory)** | SQLite + optional vector embeddings — character bible, style guides, research archive, performance history, full agent decision logs. Nothing is forgotten. |
| **Job Pipeline** | Every video is a job with stages: `IDEA → RESEARCH → SCRIPT → QC → ART → VIDEO → QC → POST → ANALYZE`, resumable, retryable. |
| **Telegram Bot** | Your boss interface — approve scripts, preview videos (MP4), one-tap approve/reject/regenerate, "make 3 variants of X," daily digest. |
| **Web Dashboard** | Pipeline board (Trello-style), agent status lights, content library, analytics charts, **cost tracker** (tokens + API spend per video). |
| **Config** | Niches, platforms, schedule, approval level (approve-everything → approve-first-2-weeks → full-auto), per-video budget cap. |

---

## 4. Tech Stack

| Piece | Choice | Cost |
|---|---|---|
| Language/Backend | Python + FastAPI (same patterns as your RUTE backend) | Free |
| Agent Brains | Plain Python agent loops (no framework lock-in) + Gemini/Claude API | ~$0.10–0.50/run |
| Vision (Video Analysis) | Gemini API (free tier) | Free |
| Images | Nano Banana / FLUX / Imagen API | ~$0.02–0.04/img |
| Video | FFmpeg free path; Veo premium path (paid) | $0 or ~$0.35/sec |
| Voice | Edge-TTS (Microsoft voices) | Free |
| Posting | Postiz self-hosted (open source) | Free (or Blotato $29/mo lazy option) |
| Interface | python-telegram-bot + FastAPI dashboard | Free |

**Software total: $0.** Realistic cost per video on free path: **under $1**.

---

## 5. Pipeline Flow

```
IDEA (Manager) 
    → RESEARCH (Researcher) 
    → SCRIPT (Scriptwriter) 
    → QC (Quality Control) 
    → ART (Art Director) 
    → VIDEO (Video Editor) 
    → QC (Quality Control) 
    → POST (Poster) 
    → ANALYZE (Analyst) 
    → (feedback loops back to RESEARCH)
```

---

## 6. Build Phases

### Phase 1 — Brain (Weeks 1)
- Project skeleton, Vault, Manager, Researcher, Scriptwriter
- Telegram bot with approval flow
- **Output:** Researched, styled scripts delivered to Telegram daily

### Phase 2 — Studio (Week 2)
- Style Analyst, Art Director, Video Editor (FFmpeg free path)
- Image generation pipeline (Nano Banana/FLUX)
- **Output:** Full MP4 videos to your Telegram for preview

### Phase 3 — Distribution (Week 3)
- QC hardening, Poster integration (Postiz self-hosted)
- Platform developer app registrations (start early — 1-4 week approvals)
- **Output:** Auto-posting begins (manual upload fallback during approvals)

### Phase 4 — Flywheel (Week 4)
- Analyst + dashboard + feedback loop
- Full-auto mode toggle
- **Output:** Self-improving system

---

## 7. Your Gemini Pro Plan — How It Fits

| Need | How Your Plan Covers It |
|---|---|
| Agent brains (research, scripts, analysis) | **Gemini API free tier** (AI Studio key, free, rate-limited — enough for personal pipeline) ✅ |
| Style analysis of reference videos | Gemini vision via same free API key ✅ |
| Images (characters, scenes) | Cheap per-image via API (~$0.02–0.04) — pennies ✅ |
| Premium AI video (Veo) | **No free API.** BUT your Pro plan = you can generate premium clips *manually* in Flow using the storyboards/prompts the agents produce — hybrid mode: agents write everything, you spend 10 min in Flow for a premium video when a video deserves it |
| Default video engine | FFmpeg free path (images + TTS + captions) — fully automated, $0 |

Your plan slots in as the **"premium tier"**: pipeline runs fully automatic on the free path, and for videos you flag as high-potential, the agents hand you a ready-made Flow prompt pack.

---

## 8. Honest Limits & Risks

- Platform posting APIs need developer-app approvals (weeks) — Phase 3 starts with manual-upload mode while approvals pend
- No virality guarantees — the ANALYST loop is how odds improve
- Full-AI-video (Veo) at scale costs real money; free path looks like "animated slideshow + voice," which is exactly what most successful faceless channels are
- First weeks need your approvals on — that's a feature, not a bug
- Copyright: extracting *style formulas* + writing original scripts + generating original visuals = safe. Copying exact content/structure = not safe. We build the safe path.

---

## 9. Project Structure (Planned)

```
D:\CONTENT-FACTORY\
├── backend/
│   ├── main.py                 # FastAPI entry
│   ├── run.py                  # Runner with lock file + signal handling
│   ├── vault/
│   │   ├── models.py           # SQLAlchemy models (jobs, agents, assets, analytics)
│   │   └── database.py         # SQLite + session
│   ├── agents/
│   │   ├── base.py             # BaseAgent class (loop, tools, memory)
│   │   ├── manager.py
│   │   ├── researcher.py
│   │   ├── style_analyst.py
│   │   ├── scriptwriter.py
│   │   ├── art_director.py
│   │   ├── video_editor.py
│   │   ├── quality_control.py
│   │   ├── poster.py
│   │   └── analyst.py
│   ├── tools/
│   │   ├── web_search.py
│   │   ├── youtube_api.py
│   │   ├── gemini_vision.py
│   │   ├── image_gen.py
│   │   ├── tts.py
│   │   ├── ffmpeg_assembler.py
│   │   └── postiz_client.py
│   ├── telegram_bot/
│   │   ├── bot.py
│   │   ├── handlers.py
│   │   └── keyboards.py
│   ├── scheduler.py            # APScheduler for cron jobs
│   └── config.py               # Pydantic settings
├── dashboard/
│   ├── main.py                 # FastAPI + Jinja2 or Next.js later
│   └── templates/
├── tests/
├── .env.example
├── requirements.txt
└── README.md
```

---

## 10. Quick-Start Commands (Future)

```bash
cd D:\CONTENT-FACTORY
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # add your API keys
python backend/run.py  # starts FastAPI + scheduler + Telegram bot
# Dashboard: http://localhost:8002 (or similar)
```

---

## 11. Next Step

Say **go** and I start Phase 1: project skeleton, vault, Manager, Researcher, Scriptwriter, Telegram approval bot — runnable the same session.

---

## 12. Source Material (Videos Referenced)

- **v5** (42s) — @ajthompson.ai — n8n beginner tutorial (Webhook → AI Agent → Email)
- **v6** (84s) — @nikothetech — Agent Reach: free Claude skill for web/YouTube/Reddit/Twitter scrape
- **v7** (2m) — @dawoodzahidd — Cartoon animation pipeline: reference video → ChatGPT style extraction → original script → character prompt → Google Flow video gen
- **v8** (1.5m) — @dawoodzahidd — Same pipeline on Cars 3: analyze movie → extract character → Nano Banana Pro → Google Flow
- **v9** (30m) — @stephenpope — n8n AI Agent deep-dive: memory, tools, testing
- **v10** (1h) — @devenseenath — YouTube Studio analytics masterclass: retention, traffic sources, growth strategy