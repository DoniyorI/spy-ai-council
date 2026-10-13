import numpy as np
import pandas as pd


def sma(series: pd.Series, n: int) -> float:
    if len(series) < n:
        return float("nan")
    return round(float(series.tail(n).mean()), 4)


def rsi(series: pd.Series, n: int = 14) -> float:
    if len(series) < n + 1:
        return float("nan")
    delta = series.diff().dropna()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.tail(n).mean()
    avg_loss = loss.tail(n).mean()
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - 100 / (1 + rs), 2)


def macd(
    series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> dict:
    if len(series) < slow + signal:
        return {"macd": float("nan"), "signal": float("nan"), "histogram": float("nan")}
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return {
        "macd": round(float(macd_line.iloc[-1]), 4),
        "signal": round(float(signal_line.iloc[-1]), 4),
        "histogram": round(float(hist.iloc[-1]), 4),
    }


def atr(df: pd.DataFrame, n: int = 14) -> float:
    if len(df) < n + 1:
        return float("nan")
    high = df["high"]
    low = df["low"]
    close = df["close"]
    tr = pd.concat(
        [
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return round(float(tr.tail(n).mean()), 4)


def vwap(df_intraday: pd.DataFrame) -> float:
    if df_intraday.empty:
        return float("nan")
    typical = (df_intraday["high"] + df_intraday["low"] + df_intraday["close"]) / 3
    vol = df_intraday["volume"]
    if vol.sum() == 0:
        return float("nan")
    return round(float((typical * vol).sum() / vol.sum()), 4)


def bollinger_bands(series: pd.Series, n: int = 20, k: float = 2) -> dict:
    if len(series) < n:
        return {"upper": float("nan"), "middle": float("nan"), "lower": float("nan")}
    mid = series.tail(n).mean()
    std = series.tail(n).std()
    return {
        "upper": round(float(mid + k * std), 4),
        "middle": round(float(mid), 4),
        "lower": round(float(mid - k * std), 4),
    }


def compute_all(df_daily: pd.DataFrame, df_intraday: pd.DataFrame) -> dict:
    close = df_daily["close"]
    bb = bollinger_bands(close)
    m = macd(close)
    return {
        "sma_10": sma(close, 10),
        "sma_50": sma(close, 50),
        "sma_200": sma(close, 200),
        "rsi_14": rsi(close),
        "macd": m["macd"],
        "macd_signal": m["signal"],
        "macd_histogram": m["histogram"],
        "atr_14": atr(df_daily),
        "vwap_today": vwap(df_intraday) if not df_intraday.empty else float("nan"),
        "bb_upper": bb["upper"],
        "bb_lower": bb["lower"],
    }
