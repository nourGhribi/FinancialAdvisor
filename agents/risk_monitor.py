"""
RiskMonitor — identifies upcoming risk events: earnings, Fed meetings,
macro data releases, and geopolitical flags from news headlines.
"""
import re
from datetime import datetime, timezone

import requests
import yfinance as yf

import config


_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; FinancialAdvisorBot/1.0)"}

# Known high-impact macro keywords to flag in headlines
_RISK_KEYWORDS = [
    "federal reserve", "fed rate", "interest rate", "rate hike", "rate cut",
    "inflation", "cpi", "ppi", "gdp", "recession", "unemployment",
    "earnings", "beats", "misses", "guidance", "outlook",
    "war", "conflict", "sanctions", "tariff", "trade war",
    "bankruptcy", "default", "downgrade", "layoffs", "restructuring",
    "sec", "investigation", "lawsuit", "regulation",
    "china", "geopolit",
]


def _fetch_earnings_calendar() -> list[dict]:
    """Fetch upcoming earnings for watchlist tickers via yfinance."""
    events = []
    for ticker in config.TICKERS:
        try:
            t = yf.Ticker(ticker)
            cal = t.calendar
            if cal is None or cal.empty:
                continue
            # calendar is a DataFrame with columns as dates and rows as metrics
            for col in cal.columns:
                date_val = col
                if hasattr(date_val, "date"):
                    date_str = date_val.date().isoformat()
                else:
                    date_str = str(date_val)
                events.append({
                    "type": "earnings",
                    "ticker": ticker,
                    "date": date_str,
                    "description": f"{ticker} earnings report",
                })
                break  # only first date
        except Exception:
            continue
    return events


def _scan_headlines_for_risks(headlines: list[dict]) -> list[dict]:
    """Flag macro/geopolitical risk from headline text."""
    alerts = []
    seen = set()
    for article in headlines:
        title = article.get("title", "").lower()
        for keyword in _RISK_KEYWORDS:
            if keyword in title and title not in seen:
                seen.add(title)
                alerts.append({
                    "type": "news_risk",
                    "keyword": keyword,
                    "title": article.get("title", ""),
                    "source": article.get("source", ""),
                    "url": article.get("url", ""),
                })
                break
    return alerts[:10]


def _vix_alert(market_data: dict) -> list[dict]:
    """Alert if VIX is elevated (fear gauge)."""
    alerts = []
    vix_data = market_data.get("indices", {}).get("VIX", {})
    vix_price = vix_data.get("price")
    if vix_price:
        if vix_price >= 30:
            alerts.append({
                "type": "vix_extreme_fear",
                "description": f"VIX at {vix_price:.1f} — extreme market fear. High volatility expected.",
            })
        elif vix_price >= 20:
            alerts.append({
                "type": "vix_elevated",
                "description": f"VIX at {vix_price:.1f} — elevated volatility. Exercise caution.",
            })
    return alerts


def run(context: dict) -> dict:
    """
    Requires context keys: macro_headlines (from NewsHarvester), market_data (from MarketDataFetcher).
    Returns:
        risk_alerts: list of risk event dicts
        earnings_calendar: upcoming earnings for watchlist
        fetched_at: ISO timestamp
    """
    macro_headlines = context.get("macro_headlines", [])
    market_data = context.get("market_data", {})

    earnings = _fetch_earnings_calendar()
    headline_risks = _scan_headlines_for_risks(macro_headlines)
    vix_alerts = _vix_alert(market_data)

    all_alerts = vix_alerts + earnings + headline_risks

    return {
        "risk_alerts": all_alerts,
        "earnings_calendar": earnings,
        "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
    }
