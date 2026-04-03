"""
Orchestrator — coordinates all agents in sequence and delivers the briefing.

Usage:
    python orchestrator.py          # run one briefing now
    python orchestrator.py --dry    # run without sending email (prints summary)
"""
import argparse
import concurrent.futures
import logging
import sys
from datetime import datetime

import pytz

import config
from agents import (
    investment_advisor,
    market_data,
    news_harvester,
    notifier,
    reddit_scout,
    risk_monitor,
    sentiment_analyst,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("orchestrator")


def run_briefing(dry_run: bool = False) -> None:
    tz = pytz.timezone(config.TIMEZONE)
    now = datetime.now(tz=tz)
    log.info("=== Starting briefing run at %s ===", now.strftime("%Y-%m-%d %H:%M %Z"))

    context: dict = {}

    # ── Phase 1: Collect data in parallel ───────────────────────────────────
    log.info("Phase 1 — collecting data (parallel)...")

    def run_reddit():
        log.info("  [RedditScout] fetching Reddit data...")
        return "reddit_data", reddit_scout.run(context)

    def run_market():
        log.info("  [MarketDataFetcher] fetching market data...")
        return "market_data", market_data.run(context)

    def run_news():
        log.info("  [NewsHarvester] fetching news feeds...")
        return "news_data", news_harvester.run(context)

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(run_reddit),
            executor.submit(run_market),
            executor.submit(run_news),
        ]
        for future in concurrent.futures.as_completed(futures):
            try:
                key, result = future.result()
                context[key] = result
                log.info("  [%s] done", key)
            except Exception as e:
                log.error("  Data agent failed: %s", e)
                # Provide empty fallback so downstream agents don't crash
                if "reddit_data" not in context:
                    context["reddit_data"] = {"trending_tickers": [], "top_posts": [], "subreddit_summary": {}}
                if "market_data" not in context:
                    context["market_data"] = {"indices": {}, "sector_etfs": {}, "watchlist": [], "market_mood": "mixed"}
                if "news_data" not in context:
                    context["news_data"] = {"macro_headlines": [], "watchlist_news": {}}

    # ── Phase 2: Risk monitor (needs news + market data) ────────────────────
    log.info("Phase 2 — running RiskMonitor...")
    try:
        context["risk_data"] = risk_monitor.run(context)
        log.info("  [RiskMonitor] done — %d alerts", len(context["risk_data"].get("risk_alerts", [])))
    except Exception as e:
        log.error("  RiskMonitor failed: %s", e)
        context["risk_data"] = {"risk_alerts": [], "earnings_calendar": []}

    # ── Phase 3: Sentiment analysis (Claude) ────────────────────────────────
    log.info("Phase 3 — SentimentAnalyst (Claude)...")
    try:
        context["sentiment_data"] = sentiment_analyst.run(context)
        log.info(
            "  [SentimentAnalyst] done — overall: %s",
            context["sentiment_data"].get("overall_market_sentiment", "?"),
        )
    except Exception as e:
        log.error("  SentimentAnalyst failed: %s", e)
        context["sentiment_data"] = {
            "sector_sentiment": [],
            "overall_market_sentiment": "neutral",
            "overall_confidence": 50,
            "analyst_note": "Sentiment analysis unavailable.",
        }

    # ── Phase 4: Investment signals (Claude) ─────────────────────────────────
    log.info("Phase 4 — InvestmentAdvisor (Claude)...")
    try:
        context["advisor_data"] = investment_advisor.run(context)
        log.info(
            "  [InvestmentAdvisor] done — top pick: %s",
            context["advisor_data"].get("top_pick", "?"),
        )
    except Exception as e:
        log.error("  InvestmentAdvisor failed: %s", e)
        context["advisor_data"] = {"signals": [], "portfolio_notes": "", "top_pick": ""}

    # ── Phase 5: Render + Send ───────────────────────────────────────────────
    if dry_run:
        log.info("Phase 5 — DRY RUN: rendering HTML only (no email sent)...")
        html = notifier.render_email(context)
        dry_path = "/tmp/financial_briefing_preview.html"
        with open(dry_path, "w") as f:
            f.write(html)
        log.info("  Preview saved to: %s", dry_path)
        log.info("  Open with: open %s", dry_path)

        # Print summary to console
        print("\n" + "=" * 60)
        print(f"MARKET MOOD: {context['market_data'].get('market_mood', '?').upper()}")
        print(f"OVERALL SENTIMENT: {context['sentiment_data'].get('overall_market_sentiment', '?').upper()}")
        print(f"TOP PICK: {context['advisor_data'].get('top_pick', '?')}")
        signals = context["advisor_data"].get("signals", [])
        if signals:
            print("\nWATCHLIST SIGNALS:")
            for s in signals:
                print(f"  {s['ticker']:<8} {s['signal']:<6} ({s.get('conviction', '?')} conviction)")
        print("=" * 60 + "\n")
    else:
        log.info("Phase 5 — sending email...")
        try:
            result = notifier.run(context)
            log.info("  [Notifier] email sent: %s", result.get("subject", ""))
        except Exception as e:
            log.error("  Notifier failed: %s", e)
            raise

    log.info("=== Briefing complete ===")


def main():
    parser = argparse.ArgumentParser(description="Financial Advisor Orchestrator")
    parser.add_argument("--dry", action="store_true", help="Render HTML only, do not send email")
    args = parser.parse_args()
    run_briefing(dry_run=args.dry)


if __name__ == "__main__":
    main()
