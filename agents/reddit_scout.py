"""
RedditScout — fetches trending posts and ticker mentions from financial subreddits.
"""
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

import praw

import config


# Common English words to exclude from ticker detection
_STOPWORDS = {
    "A", "I", "ME", "MY", "BE", "DO", "GO", "IN", "IS", "IT", "NO", "OF",
    "ON", "OR", "SO", "TO", "UP", "US", "WE", "AT", "BY", "IF", "AN", "AM",
    "AS", "HE", "HM", "OK", "PM", "AM", "DD", "EPS", "CEO", "CFO", "IPO",
    "ETF", "GDP", "CPI", "PPI", "FED", "SEC", "IMF", "WSB", "IMO", "TBH",
    "FOR", "THE", "AND", "BUT", "NOT", "ALL", "ARE", "WAS", "HAS", "HAD",
    "ITS", "ONE", "TWO", "NEW", "NOW", "OUT", "GET", "GOT", "LET", "PUT",
    "BUY", "SELL", "HOLD", "CALLS", "PUTS", "YOLO", "EOD", "AH", "IV",
    "OG", "EV", "AI", "ML",
}

_TICKER_RE = re.compile(r'\b([A-Z]{2,5})\b')


def _extract_tickers(text: str) -> list[str]:
    return [m for m in _TICKER_RE.findall(text) if m not in _STOPWORDS]


def run(context: dict) -> dict:
    """
    Returns:
        trending_tickers: list of {ticker, mentions, sentiment_score, sample_titles}
        top_posts: list of {title, subreddit, score, url, created_utc}
        subreddit_summary: dict of subreddit → {post_count, top_tickers}
    """
    reddit = praw.Reddit(
        client_id=config.REDDIT_CLIENT_ID,
        client_secret=config.REDDIT_CLIENT_SECRET,
        user_agent=config.REDDIT_USER_AGENT,
        read_only=True,
    )

    ticker_mentions: Counter = Counter()
    ticker_titles: dict[str, list[str]] = defaultdict(list)
    top_posts = []
    subreddit_summary = {}

    bullish_words = {"bull", "bullish", "moon", "buy", "long", "calls", "surge", "rally", "beat", "upside"}
    bearish_words = {"bear", "bearish", "crash", "sell", "short", "puts", "drop", "dump", "miss", "downside"}

    ticker_sentiment: dict[str, list[float]] = defaultdict(list)

    for sub_name in config.SUBREDDITS:
        sub = reddit.subreddit(sub_name)
        sub_tickers: Counter = Counter()
        post_count = 0

        try:
            posts = list(sub.hot(limit=30))
        except Exception:
            posts = []

        for post in posts:
            post_count += 1
            text = f"{post.title} {post.selftext or ''}"
            tickers = _extract_tickers(text)

            # Sentiment scoring per post
            words = set(text.lower().split())
            bull_score = len(words & bullish_words)
            bear_score = len(words & bearish_words)
            sentiment = (bull_score - bear_score) / max(bull_score + bear_score, 1)

            for t in tickers:
                ticker_mentions[t] += 1
                sub_tickers[t] += 1
                ticker_sentiment[t].append(sentiment)
                if len(ticker_titles[t]) < 3:
                    ticker_titles[t].append(post.title[:120])

            if post.score > 100:
                top_posts.append({
                    "title": post.title,
                    "subreddit": sub_name,
                    "score": post.score,
                    "url": f"https://reddit.com{post.permalink}",
                    "created_utc": datetime.fromtimestamp(post.created_utc, tz=timezone.utc).isoformat(),
                })

        subreddit_summary[sub_name] = {
            "post_count": post_count,
            "top_tickers": [t for t, _ in sub_tickers.most_common(5)],
        }

    # Build trending ticker list (top 15 by mentions)
    trending = []
    for ticker, count in ticker_mentions.most_common(15):
        sentiments = ticker_sentiment[ticker]
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0
        trending.append({
            "ticker": ticker,
            "mentions": count,
            "sentiment_score": round(avg_sentiment, 3),  # -1 bearish → +1 bullish
            "sample_titles": ticker_titles[ticker],
        })

    # Sort top_posts by score, keep top 10
    top_posts.sort(key=lambda p: p["score"], reverse=True)
    top_posts = top_posts[:10]

    return {
        "trending_tickers": trending,
        "top_posts": top_posts,
        "subreddit_summary": subreddit_summary,
    }
