from datetime import datetime, timedelta, date

import pandas as pd
import pytz

from alpaca.data.requests import StockLatestQuoteRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from src.brokers.alpaca_client import get_stock_data_client
from src.utils.time_helpers import today_et, utc_now
from src.utils.logging_config import log

ET = pytz.timezone("America/New_York")


def get_spy_quote() -> dict:
    client = get_stock_data_client()
    resp = client.get_stock_latest_quote(StockLatestQuoteRequest(symbol_or_symbols=["SPY"]))
    q = resp["SPY"]
    bid = float(q.bid_price) if q.bid_price else 0.0
    ask = float(q.ask_price) if q.ask_price else 0.0
    mid = round((bid + ask) / 2, 2) if bid and ask else 0.0
    return {"bid": bid, "ask": ask, "mid": mid, "last": mid or bid or ask}


def get_spy_bars(timeframe: str = "1Day", lookback_days: int = 90) -> pd.DataFrame:
    tf_map = {
        "1Min":  TimeFrame(1, TimeFrameUnit.Minute),
        "5Min":  TimeFrame(5, TimeFrameUnit.Minute),
        "15Min": TimeFrame(15, TimeFrameUnit.Minute),
        "1Hour": TimeFrame(1, TimeFrameUnit.Hour),
        "1Day":  TimeFrame(1, TimeFrameUnit.Day),
    }
    tf = tf_map.get(timeframe, TimeFrame(1, TimeFrameUnit.Day))
    start = utc_now() - timedelta(days=lookback_days + 5)

    client = get_stock_data_client()
    resp = client.get_stock_bars(
        StockBarsRequest(
            symbol_or_symbols=["SPY"],
            timeframe=tf,
            start=start,
            feed="iex",
        )
    )
    bars = resp["SPY"]
    if not bars:
        return pd.DataFrame()
    df = pd.DataFrame([b if isinstance(b, dict) else b.__dict__ for b in bars])
    df.columns = [c.lower() for c in df.columns]
    if "timestamp" in df.columns:
        df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def get_premarket_gap() -> dict:
    bars = get_spy_bars("1Day", 5)
    if len(bars) < 2:
        return {"gap_pct": 0.0, "prior_close": None}
    prior_close = float(bars.iloc[-2]["close"])
    quote = get_spy_quote()
    current = quote["last"] or quote["mid"]
    gap_pct = round((current - prior_close) / prior_close * 100, 3) if prior_close else 0.0
    return {"gap_pct": gap_pct, "prior_close": prior_close}


def get_volume_metrics() -> dict:
    bars = get_spy_bars("1Day", 25)
    if bars.empty:
        return {"today_volume": 0, "avg_volume_20d": 0, "volume_ratio": 0.0}
    today_vol = int(bars.iloc[-1]["volume"])
    avg_20d = int(bars.tail(21).head(20)["volume"].mean())
    ratio = round(today_vol / avg_20d, 3) if avg_20d else 0.0
    return {"today_volume": today_vol, "avg_volume_20d": avg_20d, "volume_ratio": ratio}


def get_daily_change_pct() -> float:
    bars = get_spy_bars("1Day", 3)
    if len(bars) < 2:
        return 0.0
    prior_close = float(bars.iloc[-2]["close"])
    last_close = float(bars.iloc[-1]["close"])
    return round((last_close - prior_close) / prior_close * 100, 3) if prior_close else 0.0
