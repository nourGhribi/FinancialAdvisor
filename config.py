import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent

# --- Anthropic ---
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

# --- Reddit ---
REDDIT_CLIENT_ID = os.environ["REDDIT_CLIENT_ID"]
REDDIT_CLIENT_SECRET = os.environ["REDDIT_CLIENT_SECRET"]
REDDIT_USER_AGENT = os.environ.get("REDDIT_USER_AGENT", "FinancialAdvisorBot/1.0")

# --- Email ---
GMAIL_ADDRESS = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECIPIENT_EMAIL = os.environ["RECIPIENT_EMAIL"]

# --- Schedule ---
TIMEZONE = os.environ.get("TIMEZONE", "America/Toronto")
MORNING_HOUR = int(os.environ.get("MORNING_HOUR", 7))
LUNCH_HOUR = int(os.environ.get("LUNCH_HOUR", 12))
EVENING_HOUR = int(os.environ.get("EVENING_HOUR", 18))

# --- Models ---
ANALYST_MODEL = "claude-sonnet-4-6"   # for reasoning-heavy agents
COLLECTOR_MODEL = "claude-haiku-4-5-20251001"  # not used for data agents (pure Python)

# --- Watchlist ---
with open(BASE_DIR / "watchlist.json") as f:
    WATCHLIST = json.load(f)

TICKERS = WATCHLIST["tickers"]
SECTORS = WATCHLIST["sectors"]
SUBREDDITS = WATCHLIST["subreddits"]
INDICES = WATCHLIST["indices"]
