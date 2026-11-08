# CONTENT-FACTORY

Multi-agent AI content automation pipeline for faceless social media channels.

## Overview

CONTENT-FACTORY is an automated system that researches trending topics, writes scripts, produces videos, posts to social platforms, and learns from analytics — all orchestrated by a team of AI agents with human approval gates via Telegram.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌────────────────┐
│   Telegram      │────▶│   FastAPI        │────▶│   Agents       │
│   (Approval)    │     │   Backend        │     │   (9 agents)   │
└─────────────────┘     └──────────────────┘     └────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │   Vault (SQLite) │
                        │   + Postgres     │
                        └──────────────────┘
```

## Agents

| Agent | Role |
|-------|------|
| **Manager** | Goal decomposition, job orchestration |
| **Researcher** | Trend discovery, virality scoring |
| **Style Analyst** | Video style extraction, hook formulas |
| **Scriptwriter** | Original scripts with proven formulas |
| **Art Director** | Character bibles, shot lists |
| **Video Editor** | FFmpeg assembly + premium Flow/Veo path |
| **Quality Control** | Originality, policy, retention checks |
| **Poster** | Multi-platform publishing via Postiz |
| **Analyst** | Analytics, revenue tracking, feedback loop |

## Quick Start

### Prerequisites

- Python 3.11+
- FFmpeg installed and in PATH
- Docker (for Postiz)
- Telegram Bot Token (from @BotFather)
- Google AI Studio API Key (free tier)

### Installation

```bash
cd D:\CONTENT-FACTORY

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your keys
```

### Required .env Variables

```bash
GEMINI_API_KEY=your_google_ai_studio_key
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
PEXELS_API_KEY=your_pexels_key
YOUTUBE_API_KEY=your_youtube_data_api_key
POSTIZ_API_KEY=your_postiz_key  # After Postiz setup
```

### Start Postiz (Free Self-Hosted)

```bash
docker-compose up -d
# Open http://localhost:3000 to configure Postiz
# Get API key from Postiz UI → Settings → API
```

### Run Backend

```bash
python backend/run.py
```

Backend starts at `http://localhost:8000` with Telegram bot polling.

### Usage

1. Open Telegram, message your bot
2. Send: `/goal finance 3 tiktok,youtube`
3. Research runs daily at 6 AM
4. Scripts appear in Telegram for approval
4. Approve → videos generated → posted automatically

## Commands

| Command | Description |
|---------|-------------|
| `/goal <niche> <freq> <platforms>` | Set content goal |
| `/status` | Pipeline overview |
| `/pending` | Pending approvals |
| `/approve <job_id>` | Approve current stage |
| `/reject <job_id> <reason>` | Reject with reason |
| `/variants <job_id> [n]` | Request N new script variants |
| `/preview <job_id>` | Preview script/video |
| `/premium <job_id>` | Get Flow/Veo prompt pack |
| `/cost` | Cost summary |
| `/report` | Weekly analytics report |

## Video Pipeline

### Free Path (Default)
- AI images (Pexels/local) + Edge-TTS + FFmpeg Ken Burns + captions
- Cost: ~$0/video

### Premium Path (Your Gemini Pro Plan)
- Agents generate Flow/Veo prompt packs
- You paste into Google Flow (browser) → generate clips
- Upload MP4s via `/upload_premium <job_id>`
- Cost: Covered by your $20/mo Gemini Pro plan

## Project Structure

```
D:\CONTENT-FACTORY\
├── backend/
│   ├── main.py              # FastAPI entry
│   ├── run.py               # Runner
│   ├── config.py            # Pydantic settings
│   ├── agents/              # 9 agents
│   ├── vault/               # SQLite + models
│   ├── tools/               # External integrations
│   ├── telegram_bot/        # Bot handlers
│   └── scheduler/           # APScheduler jobs
├── dashboard/               # Web UI (Phase 4)
├── tests/
├── .env.example
├── requirements.txt
└── docker-compose.yml       # Postiz + Postgres + Redis
```

## Cost Model

| Component | Cost |
|-----------|------|
| Software | $0 (all open source) |
| LLM (Gemini free tier) | Free |
| Images (Pexels) | Free |
| TTS (Edge-TTS) | Free |
| Video (FFmpeg) | Free |
| Posting (Postiz) | Free |
| **Total** | **$0** |
| Premium video (Veo) | Your Gemini Pro plan |

## Development

```bash
# Run tests
pytest tests/ -v

# Format code
black backend/

# Type check
mypy backend/
```

## Phase Status

- [x] Phase 1: Brain (Research → Scripts)
- [ ] Phase 2: Studio (Video generation)
- [ ] Phase 3: Distribution (Posting)
- [ ] Phase 4: Flywheel (Analytics + Dashboard)

## License

MIT