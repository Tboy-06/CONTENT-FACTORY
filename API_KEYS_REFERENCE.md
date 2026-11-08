# API KEY QUICK REFERENCE CARD
# =============================
# Copy .env.example to .env, then replace each "your_*" value

## REQUIRED (Bot won't work without these)
| Key | Format Example | Where to Get |
|-----|----------------|--------------|
| GEMINI_API_KEY | `AIzaSyB1cD3eF5gH7jK9mN1pQ3rS5tU7vW9xY` | https://aistudio.google.com/apikey |
| TELEGRAM_BOT_TOKEN | `123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ` | @BotFather → /newbot |
| TELEGRAM_CHAT_ID | `123456789` | @userinfobot |
| TELEGRAM_ALLOWED_USERS_RAW | `123456789,987654321` | Your chat ID(s) |

## REQUIRED FOR RESEARCHER
| Key | Format Example | Where to Get |
|-----|----------------|--------------|
| YOUTUBE_API_KEY | `AIzaSyC2dE4fG6hJ8kL0mN2pQ4rS6tU8vW0xY` | Google Cloud Console → YouTube Data API v3 |
| PEXELS_API_KEY | `563492ad6f91700001000001aBcDeFgHiJkLmNoP` | https://www.pexels.com/api/ |

## OPTIONAL BUT RECOMMENDED
| Key | Format Example | Where to Get | Free Tier |
|-----|----------------|--------------|-----------|
| TAVILY_API_KEY | `tvly-abcdefghijklmnopqrstuvwxyz123456` | https://tavily.com/ | 1,000/mo |
| SERPAPI_KEY | `abcdefghijklmnopqrstuvwxyz123456` | https://serpapi.com/ | 100/mo |
| FIRECRAWL_API_KEY | `fc-abcdefghijklmnopqrstuv` | https://firecrawl.dev/ | Free tier |

## POSTING (Phase 3+)
| Key | Format Example | Where to Get |
|-----|----------------|--------------|
| POSTIZ_API_KEY | `pz_abcdefghijklmnopqrstuvwxyz123456` | Postiz UI → Settings → API (after docker-compose up) |

---

## STEP-BY-STEP: GET EACH KEY

### 1. GEMINI_API_KEY (2 min)
1. Go to https://aistudio.google.com/apikey
2. Sign in with Google
3. Click "Create API Key"
3. Copy key (starts with `AIzaSy`)

### 2. TELEGRAM_BOT_TOKEN (3 min)
1. Open Telegram, search `@BotFather`
2. Send `/newbot`
3. Name: `My Content Factory`
4. Username: `mycontentfactory_bot` (must end in `_bot`)
5. Copy token (format: `123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ`)

### 3. TELEGRAM_CHAT_ID (1 min)
1. Search `@userinfobot` on Telegram
2. Send `/start`
3. Copy your numeric ID (e.g., `123456789`)

### 4. YOUTUBE_API_KEY (5 min)
1. Go to https://console.cloud.google.com/
2. Create project or select existing
3. Enable "YouTube Data API v3"
4. Go to Credentials → Create Credentials → API Key
5. Restrict key to "YouTube Data API v3"
6. Copy key (starts with `AIzaSy`)

### 5. PEXELS_API_KEY (2 min)
1. Go to https://www.pexels.com/api/
2. Sign up / log in
3. Copy API key

### 6. TAVILY_API_KEY (2 min) - Optional
1. Go to https://tavily.com/
2. Sign up
3. Copy key (starts with `tvly-`)

### 7. POSTIZ_API_KEY (After Docker) - Phase 3
1. Run `docker-compose up -d`
2. Open http://localhost:3000
3. Create account
4. Settings → API → Copy key (starts with `pz_`)

---

## VERIFY YOUR .env

Run this to check all required keys are set:
```powershell
cd D:\CONTENT-FACTORY
.venv\Scripts\python -c "
from backend.config import get_settings
s = get_settings()
checks = [
    ('GEMINI_API_KEY', bool(s.gemini_api_key)),
    ('TELEGRAM_BOT_TOKEN', bool(s.telegram_bot_token)),
    ('TELEGRAM_CHAT_ID', bool(s.telegram_chat_id)),
    ('YOUTUBE_API_KEY', bool(s.youtube_api_key)),
    ('PEXELS_API_KEY', bool(s.pexels_api_key)),
]
for name, ok in checks:
    print(f'{'OK' if ok else 'MISSING'}: {name}')
"
```

---

## KEY FORMATS AT A GLANCE

```
GEMINI_API_KEY          → AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
TELEGRAM_BOT_TOKEN      → 123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ
TELEGRAM_CHAT_ID        → 123456789
YOUTUBE_API_KEY         → AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
PEXELS_API_KEY          → 563492ad6f91700001000001XXXXXXXXXXXXXXXX
TAVILY_API_KEY          → tvly-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
SERPAPI_KEY             → xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
FIRECRAWL_API_KEY       → fc-XXXXXXXXXXXXXXXXXXXXXX
POSTIZ_API_KEY          → pz_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

**Never commit real keys to git.** The `.gitignore` already excludes `.env`.