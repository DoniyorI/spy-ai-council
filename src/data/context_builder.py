from datetime import date
import math

from src.data.market_data import (
    get_spy_quote,
    get_spy_bars,
    get_premarket_gap,
    get_volume_metrics,
    get_daily_change_pct,
)
from src.data.options_data import fetch_chain, compute_greeks_if_missing, slice_chain_by_type
from src.data.news_data import get_recent_news
from src.data.indicators import compute_all
from src.brokers.alpaca_client import get_account
from src.utils.time_helpers import utc_now, today_et
from src.utils.logging_config import log


def _trend_summary(sma10: float, sma50: float, sma200: float) -> dict:
    def _dir(a, b):
        if math.isnan(a) or math.isnan(b):
            return "unknown"
        return "bullish" if a > b else "bearish"

    short = _dir(sma10, sma50)
    medium = _dir(sma50, sma200)
    long_ = _dir(sma10, sma200)

    if sma10 > sma50 > sma200:
        alignment = "10>50>200"
    elif sma10 < sma50 < sma200:
        alignment = "10<50<200"
    else:
        alignment = "mixed"

    return {
        "short_term": short,
        "medium_term": medium,
        "long_term": long_,
        "alignment": alignment,
    }


def build_context() -> dict:
    log.info("Building market context...")

    # Fetch raw data
    quote = get_spy_quote()
    bars_30d = get_spy_bars("1Day", 35)
    bars_90d = get_spy_bars("1Day", 95)
    bars_intraday = get_spy_bars("5Min", 2)
    gap_info = get_premarket_gap()
    volume_info = get_volume_metrics()
    daily_chg = get_daily_change_pct()
    news = get_recent_news(hours=24, limit=15)
    account = get_account()

    # Indicators (use 90d bars for SMA200, intraday for VWAP)
    indicators = compute_all(bars_90d, bars_intraday)
    trend = _trend_summary(
        indicators.get("sma_10", float("nan")),
        indicators.get("sma_50", float("nan")),
        indicators.get("sma_200", float("nan")),
    )

    # Options chain — wide pull, then slice by type
    chain = fetch_chain(min_dte=1, max_dte=45)
    spot = quote["last"]
    if not chain.empty and spot:
        chain = compute_greeks_if_missing(chain, spot)
    options_universe = slice_chain_by_type(chain) if not chain.empty else {}

    # Trim options to 5-6 near-ATM strikes per bucket/side to keep token count low
    def _trim_strikes(contracts: list[dict], n: int = 6) -> list[dict]:
        if not contracts or not spot:
            return contracts[:n]
        return sorted(contracts, key=lambda c: abs((c.get("strike") or 0) - spot))[:n]

    for tt in options_universe:
        options_universe[tt]["calls"] = _trim_strikes(options_universe[tt]["calls"])
        options_universe[tt]["puts"] = _trim_strikes(options_universe[tt]["puts"])

    # Macro flags (manual overrides via env; future: use calendar API)
    import os
    is_fomc = os.getenv("IS_FOMC_WEEK", "false").lower() == "true"
    is_cpi = os.getenv("IS_CPI_WEEK", "false").lower() == "true"
    is_earnings = os.getenv("IS_EARNINGS_WEEK_MEGACAP", "false").lower() == "true"

    ctx = {
        "as_of": utc_now().isoformat(),
        "ticker": "SPY",
        "account": {
            "equity": account["equity"],
            "cash": account["cash"],
            "buying_power": account["buying_power"],
            "open_positions": len([p for p in [] if True]),  # filled by orchestrator
            "trades_today": 0,  # filled by orchestrator
            "max_trade_size_usd": 100,
            "max_trades_today": 2,
        },
        "spot": {
            "last": spot,
            "bid": quote["bid"],
            "ask": quote["ask"],
            "prior_close": gap_info["prior_close"],
            "daily_change_pct": daily_chg,
            "premarket_gap_pct": gap_info["gap_pct"],
        },
        "volume": {
            "today": volume_info["today_volume"],
            "avg_20d": volume_info["avg_volume_20d"],
            "ratio": volume_info["volume_ratio"],
        },
        "indicators": indicators,
        "trend_summary": trend,
        "options_universe": options_universe,
        "news_last_24h": news[:10],
        "vix": None,  # v2: add yfinance ^VIX pull
        "is_fomc_week": is_fomc,
        "is_cpi_week": is_cpi,
        "is_earnings_week_for_megacaps": is_earnings,
    }

    log.info(f"Context built: spot={spot}, rsi={indicators.get('rsi_14')}, news={len(news)}")
    return ctx
