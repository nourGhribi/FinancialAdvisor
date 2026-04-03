"""
MarketDataFetcher — retrieves live market data via yfinance.
Covers indices, sector ETFs, and the user's watchlist tickers.
"""
from datetime import datetime, timezone

import yfinance as yf

import config


def _pct(current: float, prev: float) -> float:
    if prev == 0:
        return 0.0
    return round((current - prev) / prev * 100, 2)


def _fetch_ticker(symbol: str) -> dict:
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="2d")
        if len(hist) < 2:
            hist = t.history(period="5d")
        if hist.empty:
            return {"symbol": symbol, "error": "no data"}

        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) >= 2 else hist.iloc[-1]

        info = {}
        try:
            info = t.fast_info
        except Exception:
            pass

        return {
            "symbol": symbol,
            "price": round(float(latest["Close"]), 2),
            "open": round(float(latest["Open"]), 2),
            "high": round(float(latest["High"]), 2),
            "low": round(float(latest["Low"]), 2),
            "volume": int(latest["Volume"]),
            "pct_change_1d": _pct(float(latest["Close"]), float(prev["Close"])),
            "market_cap": getattr(info, "market_cap", None),
            "fifty_two_week_high": getattr(info, "year_high", None),
            "fifty_two_week_low": getattr(info, "year_low", None),
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}


def run(context: dict) -> dict:
    """
    Returns:
        indices: dict of index → {price, pct_change_1d}
        sector_etfs: dict of sector → {etf, price, pct_change_1d}
        watchlist: list of ticker data dicts
        market_mood: overall directional string ("bullish" | "mixed" | "bearish")
        fetched_at: ISO timestamp
    """
    # --- Indices ---
    indices = {}
    index_labels = {
        "^GSPC": "S&P 500",
        "^IXIC": "NASDAQ",
        "^DJI": "Dow Jones",
        "^VIX": "VIX",
    }
    for symbol in config.INDICES:
        data = _fetch_ticker(symbol)
        label = index_labels.get(symbol, symbol)
        indices[label] = data

    # --- Sector ETFs (one per sector) ---
    sector_etf_map = {
        sector: tickers[0]  # first entry is the ETF
        for sector, tickers in config.SECTORS.items()
        if tickers and tickers[0].startswith("XL")
    }
    sector_etfs = {}
    for sector, etf in sector_etf_map.items():
        data = _fetch_ticker(etf)
        sector_etfs[sector] = {"etf": etf, **data}

    # --- Watchlist ---
    watchlist = [_fetch_ticker(t) for t in config.TICKERS]

    # --- Market mood (simple heuristic) ---
    changes = [
        d["pct_change_1d"]
        for d in list(indices.values()) + list(sector_etfs.values())
        if "pct_change_1d" in d
    ]
    if changes:
        avg = sum(changes) / len(changes)
        market_mood = "bullish" if avg > 0.3 else "bearish" if avg < -0.3 else "mixed"
    else:
        market_mood = "mixed"

    return {
        "indices": indices,
        "sector_etfs": sector_etfs,
        "watchlist": watchlist,
        "market_mood": market_mood,
        "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
    }
