"""
InvestmentAdvisor — uses Claude to generate Buy/Sell/Hold signals for each
watchlist ticker, grounded in market data, news, Reddit sentiment, and sector analysis.
"""
import json

import anthropic

import config


_SYSTEM_PROMPT = """You are a senior equity analyst and portfolio strategist.
You synthesize market data, news sentiment, Reddit community signals, and sector trends
to generate actionable investment signals for individual stocks.

IMPORTANT DISCLAIMER: This is AI-generated analysis for informational purposes only.
It is NOT financial advice. Always do your own research and consult a licensed advisor.

Respond with valid JSON only — no markdown, no text outside the JSON.
"""

_USER_TEMPLATE = """Generate investment signals for the following watchlist tickers.

## Overall Market Sentiment
{overall_sentiment} (confidence: {overall_confidence}%)
Analyst note: {analyst_note}

## Sector Sentiment
{sector_sentiment}

## Watchlist Price Data
{watchlist_prices}

## Ticker-Specific News
{ticker_news}

## Reddit Mentions (from trending list)
{reddit_mentions}

## Risk Alerts
{risk_alerts}

## Task
For EACH ticker in the watchlist, output a signal. Use this exact JSON schema:
{{
  "signals": [
    {{
      "ticker": "AAPL",
      "signal": "BUY" | "HOLD" | "SELL" | "AVOID",
      "conviction": "high" | "medium" | "low",
      "price": <current price float>,
      "reasoning": "<2-3 sentences with key thesis>",
      "catalysts": ["<positive catalyst 1>", ...],
      "risks": ["<risk 1>", ...],
      "time_horizon": "short-term (days)" | "medium-term (weeks)" | "long-term (months)"
    }},
    ...
  ],
  "portfolio_notes": "<2-3 sentences of overall portfolio commentary>",
  "top_pick": "<ticker symbol of the single strongest opportunity today>"
}}

Provide signals for ALL tickers: {tickers}
"""


def _format_watchlist_prices(watchlist: list) -> str:
    lines = []
    for item in watchlist:
        if "error" in item:
            lines.append(f"- {item['symbol']}: data unavailable")
        else:
            lines.append(
                f"- {item['symbol']}: ${item.get('price', 0):.2f} "
                f"({item.get('pct_change_1d', 0):+.2f}% today) "
                f"| H: ${item.get('high', 0):.2f} L: ${item.get('low', 0):.2f}"
            )
    return "\n".join(lines)


def _format_sector_sentiment(sectors: list) -> str:
    lines = []
    for s in sectors:
        emoji = {"bullish": "🟢", "neutral": "🟡", "bearish": "🔴"}.get(s.get("sentiment", ""), "⚪")
        lines.append(
            f"- {emoji} {s['sector']}: {s['sentiment'].upper()} ({s['confidence']}%) — {s.get('rationale', '')}"
        )
    return "\n".join(lines) if lines else "No sector data."


def _format_ticker_news(watchlist_news: dict) -> str:
    lines = []
    for ticker, articles in watchlist_news.items():
        headlines = "; ".join(a.get("title", "") for a in articles[:2])
        lines.append(f"- {ticker}: {headlines}")
    return "\n".join(lines) if lines else "No ticker-specific news."


def _format_reddit_mentions(trending: list, tickers: list) -> str:
    ticker_set = set(tickers)
    lines = []
    for item in trending:
        if item["ticker"] in ticker_set:
            score = item.get("sentiment_score", 0)
            direction = "bullish" if score > 0.1 else "bearish" if score < -0.1 else "neutral"
            lines.append(
                f"- {item['ticker']}: {item['mentions']} Reddit mentions ({direction})"
            )
    return "\n".join(lines) if lines else "No Reddit data for watchlist."


def _format_risk_alerts(alerts: list) -> str:
    lines = []
    for alert in alerts[:8]:
        if alert.get("type") == "earnings":
            lines.append(f"- EARNINGS: {alert['ticker']} reports on {alert['date']}")
        elif alert.get("type") in ("vix_extreme_fear", "vix_elevated"):
            lines.append(f"- VOLATILITY: {alert['description']}")
        elif alert.get("type") == "news_risk":
            lines.append(f"- NEWS RISK [{alert.get('keyword', '').upper()}]: {alert.get('title', '')}")
    return "\n".join(lines) if lines else "No significant risk alerts."


def run(context: dict) -> dict:
    """
    Requires context: market_data, news_data, reddit_data, sentiment_data, risk_data.
    Returns:
        signals: list of per-ticker signal objects
        portfolio_notes: str
        top_pick: str
    """
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    market_data = context.get("market_data", {})
    news_data = context.get("news_data", {})
    reddit_data = context.get("reddit_data", {})
    sentiment_data = context.get("sentiment_data", {})
    risk_data = context.get("risk_data", {})

    user_message = _USER_TEMPLATE.format(
        overall_sentiment=sentiment_data.get("overall_market_sentiment", "neutral"),
        overall_confidence=sentiment_data.get("overall_confidence", 50),
        analyst_note=sentiment_data.get("analyst_note", ""),
        sector_sentiment=_format_sector_sentiment(sentiment_data.get("sector_sentiment", [])),
        watchlist_prices=_format_watchlist_prices(market_data.get("watchlist", [])),
        ticker_news=_format_ticker_news(news_data.get("watchlist_news", {})),
        reddit_mentions=_format_reddit_mentions(
            reddit_data.get("trending_tickers", []), config.TICKERS
        ),
        risk_alerts=_format_risk_alerts(risk_data.get("risk_alerts", [])),
        tickers=", ".join(config.TICKERS),
    )

    response = client.messages.create(
        model=config.ANALYST_MODEL,
        max_tokens=2500,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    result = json.loads(raw)
    return {
        "signals": result.get("signals", []),
        "portfolio_notes": result.get("portfolio_notes", ""),
        "top_pick": result.get("top_pick", ""),
    }
