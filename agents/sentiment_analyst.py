"""
SentimentAnalyst — uses Claude to score each sector's sentiment based on
collected news, Reddit data, and market price action.
"""
import json

import anthropic

import config


_SYSTEM_PROMPT = """You are a quantitative financial sentiment analyst.
You receive raw data (news headlines, Reddit mentions, and sector ETF price changes)
and produce a structured sentiment analysis for each market sector.

You MUST respond with valid JSON only — no markdown, no explanation outside the JSON.
"""

_USER_TEMPLATE = """Analyze the sentiment for each sector listed below.

## Sector ETF Performance (1-day % change)
{sector_performance}

## Reddit Trending Tickers (mentions + sentiment score -1 to +1)
{reddit_tickers}

## Recent News Headlines (sample)
{headlines}

## Task
For each sector, output a JSON object with this exact schema:
{{
  "sectors": [
    {{
      "sector": "Technology",
      "sentiment": "bullish" | "neutral" | "bearish",
      "confidence": <integer 0-100>,
      "rationale": "<1-2 sentence explanation>",
      "key_drivers": ["<driver1>", "<driver2>"]
    }},
    ...
  ],
  "overall_market_sentiment": "bullish" | "neutral" | "bearish",
  "overall_confidence": <integer 0-100>,
  "analyst_note": "<2-3 sentence market overview>"
}}

Include all sectors from the ETF performance data.
"""


def _format_sector_performance(sector_etfs: dict) -> str:
    lines = []
    for sector, data in sector_etfs.items():
        pct = data.get("pct_change_1d", 0)
        lines.append(f"- {sector} ({data.get('etf', '?')}): {pct:+.2f}%")
    return "\n".join(lines) if lines else "No data available."


def _format_reddit_tickers(trending: list) -> str:
    lines = []
    for item in trending[:10]:
        score = item.get("sentiment_score", 0)
        direction = "bullish" if score > 0.1 else "bearish" if score < -0.1 else "neutral"
        lines.append(
            f"- {item['ticker']}: {item['mentions']} mentions, sentiment={score:+.2f} ({direction})"
        )
    return "\n".join(lines) if lines else "No Reddit data available."


def _format_headlines(headlines: list) -> str:
    lines = []
    for h in headlines[:15]:
        title = h.get("title", "")
        source = h.get("source", "")
        if title:
            lines.append(f"- [{source}] {title}")
    return "\n".join(lines) if lines else "No headlines available."


def run(context: dict) -> dict:
    """
    Requires context: market_data, reddit_data, news_data.
    Returns:
        sector_sentiment: list of sector sentiment objects
        overall_market_sentiment: str
        overall_confidence: int
        analyst_note: str
    """
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    sector_etfs = context.get("market_data", {}).get("sector_etfs", {})
    trending_tickers = context.get("reddit_data", {}).get("trending_tickers", [])
    headlines = context.get("news_data", {}).get("macro_headlines", [])

    user_message = _USER_TEMPLATE.format(
        sector_performance=_format_sector_performance(sector_etfs),
        reddit_tickers=_format_reddit_tickers(trending_tickers),
        headlines=_format_headlines(headlines),
    )

    response = client.messages.create(
        model=config.ANALYST_MODEL,
        max_tokens=1500,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    result = json.loads(raw)
    return {
        "sector_sentiment": result.get("sectors", []),
        "overall_market_sentiment": result.get("overall_market_sentiment", "neutral"),
        "overall_confidence": result.get("overall_confidence", 50),
        "analyst_note": result.get("analyst_note", ""),
    }
