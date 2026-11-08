# CONTENT-FACTORY

A Multi-Agent AI Content Automation Pipeline utilizing 9 Agents to fully automate the short-form video lifecycle from ideation to analytics.

## Quick Start (Python Backend)

### 1. Environment Setup
```bash
python -m venv venv
# Linux / macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and configure your API keys:
```bash
cp .env.example .env
```
Key configuration items:
- `GEMINI_API_KEY`: Your Google Gemini API key
- `TELEGRAM_BOT_TOKEN`: Telegram bot token from @BotFather
- `TELEGRAM_ALLOWED_USERS_RAW`: Comma-separated allowed Telegram user IDs
- `DAILY_BUDGET_USD`: Maximum daily spend limit (e.g., 5.0)

### 3. Run the Services
```bash
# Start Docker services (Postiz, Postgres, Redis):
docker-compose up -d

# Run the backend and dashboard:
python run_backend.py
```
The dashboard will be available at: `http://localhost:8000`

### 4. Running Tests
```bash
pytest tests/
```

---

## Telegram Bot Commands
Message your bot with any of the following:
- `/goal <niche>` - Create a new video pipeline
- `/status` - Check all active pipeline jobs
- `/pending` - View jobs awaiting human approval
- `/approve <id>` - Approve current stage
- `/reject <id> <reason>` - Reject and request revision
- `/variants <id>` - View alternative hook angles
- `/preview <id>` - Preview generated script and media assets
- `/premium <id>` - Enable premium Veo mode
- `/upload_premium <id>` - Attach a custom video render
- `/post <id>` - Post immediately to social platforms
- `/analyze <id>` - View virality and retention metrics
- `/cost` - Check token spend against daily budget
- `/report` - Daily executive operations report
- `/help` - Command documentation
