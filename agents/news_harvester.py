"""
NewsHarvester — collects recent financial headlines from Yahoo Finance and Reuters RSS feeds.
"""
from datetime import datetime, timezone

import feedparser
import requests

import config


_FEEDS = [
    # Yahoo Finance
    ("Yahoo Finance - Top Stories", "https://finance.yahoo.com/rss/topstories"),
    ("Yahoo Finance - Markets", "https://finance.yahoo.com/rss/markets"),
    ("Yahoo Finance - Technology", "https://finance.yahoo.com/rss/topic/tech"),
    # Reuters
    ("Reuters - Business", "https://feeds.reuters.com/reuters/businessNews"),
    ("Reuters - Technology", "https://feeds.reuters.com/reuters/technologyNews"),
    # Seeking Alpha (public RSS)
    ("Seeking Alpha - Market News", "https://seekingalpha.com/market_currents.xml"),
    # CNBC
    ("CNBC - Top News", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
]

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; FinancialAdvisorBot/1.0)"
}


def _parse_feed(name: str, url: str) -> list[dict]:
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        feed = feedparser.parse(resp.content)
        articles = []
        for entry in feed.entries[:8]:
            published = entry.get("published", entry.get("updated", ""))
            articles.append({
                "source": name,
                "title": entry.get("title", "").strip(),
                "summary": entry.get("summary", "")[:300].strip(),
                "url": entry.get("link", ""),
                "published": published,
            })
        return articles
    except Exception as e:
        return [{"source": name, "error": str(e)}]


def _ticker_news(ticker: str) -> list[dict]:
    """Fetch Yahoo Finance RSS for a specific ticker."""
    url = f"https://finance.yahoo.com/rss/headline?s={ticker}"
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=8)
        feed = feedparser.parse(resp.content)
        articles = []
        for entry in feed.entries[:4]:
            articles.append({
                "source": f"Yahoo Finance ({ticker})",
                "title": entry.get("title", "").strip(),
                "summary": entry.get("summary", "")[:300].strip(),
                "url": entry.get("link", ""),
                "published": entry.get("published", ""),
            })
        return articles
    except Exception:
        return []


def run(context: dict) -> dict:
    """
    Returns:
        macro_headlines: top general financial news articles
        watchlist_news: news articles specific to each watchlist ticker
        fetched_at: ISO timestamp
    """
    # Macro news from all feeds
    macro_headlines = []
    for name, url in _FEEDS:
        macro_headlines.extend(_parse_feed(name, url))

    # Remove entries with errors, deduplicate by title
    seen_titles = set()
    clean_macro = []
    for article in macro_headlines:
        if "error" in article:
            continue
        title = article.get("title", "")
        if title and title not in seen_titles:
            seen_titles.add(title)
            clean_macro.append(article)

    # Cap at 25 macro headlines
    clean_macro = clean_macro[:25]

    # Per-ticker news (only for watchlist)
    watchlist_news = {}
    for ticker in config.TICKERS:
        articles = _ticker_news(ticker)
        if articles:
            watchlist_news[ticker] = articles

    return {
        "macro_headlines": clean_macro,
        "watchlist_news": watchlist_news,
        "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
    }
