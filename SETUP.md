# Financial Advisor — Setup Guide

## 1. Prerequisites

- Python 3.12+
- A Reddit account
- A Gmail account with 2FA enabled
- An Anthropic API key

---

## 2. Local Setup

```bash
cd "FinancialAdvisor"
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your credentials (see below for each service).

---

## 3. Get API Keys

### Anthropic API Key
- Visit https://console.anthropic.com → API Keys → Create key
- Add to `.env`: `ANTHROPIC_API_KEY=sk-ant-...`

### Reddit API
1. Go to https://www.reddit.com/prefs/apps
2. Click "create app" → choose **script**
3. Name: `FinancialAdvisorBot`, redirect URI: `http://localhost`
4. Copy **client_id** (under app name) and **client_secret**
5. Add to `.env`:
   ```
   REDDIT_CLIENT_ID=your_id
   REDDIT_CLIENT_SECRET=your_secret
   REDDIT_USER_AGENT=FinancialAdvisorBot/1.0 by /u/your_username
   ```

### Gmail App Password
1. Enable 2-Factor Authentication on your Google account
2. Go to: Google Account → Security → 2-Step Verification → App Passwords
3. Create a new app password (name it "FinancialAdvisor")
4. Add to `.env`:
   ```
   GMAIL_ADDRESS=you@gmail.com
   GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
   RECIPIENT_EMAIL=you@gmail.com
   ```

---

## 4. Customize Your Watchlist

Edit `watchlist.json` to add/remove tickers:
```json
{
  "tickers": ["AAPL", "NVDA", "MSFT", ...],
  ...
}
```

---

## 5. Test Locally

```bash
# Run one briefing immediately, preview HTML (no email sent)
python orchestrator.py --dry

# Opens the preview in your browser
open /tmp/financial_briefing_preview.html

# Run a real briefing and send the email
python orchestrator.py
```

---

## 6. Deploy to Railway

1. Install Railway CLI: https://docs.railway.app/develop/cli
2. Create a new project:
   ```bash
   railway login
   railway init
   railway up
   ```
3. Set environment variables in the Railway dashboard:
   - Go to your project → Variables tab
   - Add all variables from your `.env` file
4. The container will start automatically and run `scheduler.py`
5. Verify in Railway → Deployments → Logs

### Alternative: DigitalOcean App Platform
1. Push code to GitHub
2. Create a new App → link your repo
3. Set environment variables in the App settings
4. Deploy

---

## 7. Schedule

The system runs 3x daily (in your configured timezone):
| Time | Briefing |
|------|----------|
| 07:00 | Morning — pre-market, overnight news |
| 12:00 | Midday — intraday update |
| 18:00 | Evening — closing summary |

Change times in `.env`:
```
MORNING_HOUR=7
LUNCH_HOUR=12
EVENING_HOUR=18
```
