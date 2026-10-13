from datetime import date, timedelta
from math import log, sqrt, exp
from statistics import NormalDist

import pandas as pd

from alpaca.data.requests import OptionChainRequest, OptionLatestQuoteRequest

from config.settings import TRADE_TYPE_CONFIG
from src.brokers.alpaca_client import get_option_data_client
from src.utils.time_helpers import today_et, dte as calc_dte
from src.utils.logging_config import log

_NORM = NormalDist()


def _bs_greeks(S: float, K: float, T: float, r: float, sigma: float, opt_type: str) -> dict:
    """Black-Scholes delta/gamma/theta/vega fallback."""
    if T <= 0 or sigma <= 0:
        return {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0}
    d1 = (log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt(T))
    d2 = d1 - sigma * sqrt(T)
    gamma = _NORM.pdf(d1) / (S * sigma * sqrt(T))
    vega = S * _NORM.pdf(d1) * sqrt(T) / 100
    if opt_type == "call":
        delta = _NORM.cdf(d1)
        theta = (
            -S * _NORM.pdf(d1) * sigma / (2 * sqrt(T))
            - r * K * exp(-r * T) * _NORM.cdf(d2)
        ) / 365
    else:
        delta = _NORM.cdf(d1) - 1
        theta = (
            -S * _NORM.pdf(d1) * sigma / (2 * sqrt(T))
            + r * K * exp(-r * T) * _NORM.cdf(-d2)
        ) / 365
    return {
        "delta": round(delta, 4),
        "gamma": round(gamma, 4),
        "theta": round(theta, 4),
        "vega": round(vega, 4),
    }


def _parse_occ_symbol(symbol: str) -> tuple[str, date, float]:
    """Parse OCC option symbol → (type, expiration, strike).
    Format: SPY260515P00525000 → put, 2026-05-15, 525.0
    """
    # underlying is variable length; last 15 chars are fixed: YYMMDD + C/P + 8-digit strike
    suffix = symbol[-15:]
    yy, mm, dd = int(suffix[0:2]), int(suffix[2:4]), int(suffix[4:6])
    opt_type = "call" if suffix[6] == "C" else "put"
    strike = int(suffix[7:15]) / 1000.0
    exp = date(2000 + yy, mm, dd)
    return opt_type, exp, strike


def fetch_chain(min_dte: int = 1, max_dte: int = 45) -> pd.DataFrame:
    today = today_et()
    exp_from = (today + timedelta(days=min_dte)).isoformat()
    exp_to = (today + timedelta(days=max_dte)).isoformat()

    client = get_option_data_client()
    try:
        resp = client.get_option_chain(
            OptionChainRequest(
                underlying_symbol="SPY",
                expiration_date_gte=exp_from,
                expiration_date_lte=exp_to,
                feed="indicative",
            )
        )
    except Exception as e:
        log.error(f"fetch_chain error: {e}")
        return pd.DataFrame()

    rows = []
    for symbol, snap in resp.items():
        if not hasattr(snap, "latest_quote"):
            continue
        q = snap.latest_quote

        try:
            opt_type, exp_date, strike = _parse_occ_symbol(symbol)
        except Exception:
            continue

        d = calc_dte(exp_date)
        bid = float(q.bid_price) if q.bid_price else 0.0
        ask = float(q.ask_price) if q.ask_price else 0.0
        mid = round((bid + ask) / 2, 3) if bid and ask else 0.0
        iv = float(snap.implied_volatility) if snap.implied_volatility else None

        greeks = snap.greeks
        delta = float(greeks.delta) if greeks and greeks.delta is not None else None
        gamma = float(greeks.gamma) if greeks and greeks.gamma is not None else None
        theta = float(greeks.theta) if greeks and greeks.theta is not None else None
        vega  = float(greeks.vega)  if greeks and greeks.vega  is not None else None

        rows.append({
            "symbol": symbol,
            "strike": strike,
            "expiration": exp_date.isoformat(),
            "dte": d,
            "type": opt_type,
            "bid": bid,
            "ask": ask,
            "mid": mid,
            "spread_pct": round((ask - bid) / mid * 100, 2) if mid else 999,
            "volume": int((getattr(q, "bid_size", 0) or 0) + (getattr(q, "ask_size", 0) or 0)),
            "open_interest": 0,  # not in OptionsSnapshot v0.43
            "implied_volatility": iv,
            "delta": delta,
            "gamma": gamma,
            "theta": theta,
            "vega": vega,
        })

    return pd.DataFrame(rows)


def compute_greeks_if_missing(chain: pd.DataFrame, spot: float, r: float = 0.05) -> pd.DataFrame:
    today = today_et()
    for idx, row in chain.iterrows():
        if row.get("delta") is not None:
            continue
        T = row["dte"] / 365 if row["dte"] else 0
        iv = row["implied_volatility"] or 0.20
        if row["strike"] and T > 0:
            greeks = _bs_greeks(spot, row["strike"], T, r, iv, row["type"] or "call")
            for k, v in greeks.items():
                chain.at[idx, k] = v
    return chain


def filter_liquid(chain: pd.DataFrame, trade_type: str | None = None) -> pd.DataFrame:
    df = chain.copy()
    df = df[(df["bid"] > 0) & (df["ask"] > 0) & (df["mid"] >= 0.20)]

    if trade_type and trade_type in TRADE_TYPE_CONFIG:
        cfg = TRADE_TYPE_CONFIG[trade_type]
        df = df[df["dte"].between(cfg["dte_min"], cfg["dte_max"])]
        df = df[df["spread_pct"] <= cfg["max_spread_pct"]]
        df = df[df["open_interest"] >= cfg["min_open_interest"]]
        df = df[df["volume"] >= cfg["min_volume"]]
        df = df[df["mid"] * 100 <= cfg["max_position_size_usd"]]
    else:
        df = df[df["spread_pct"] <= 15]

    return df.reset_index(drop=True)


def slice_chain_by_type(chain: pd.DataFrame) -> dict[str, dict[str, list]]:
    result = {}
    for tt, cfg in TRADE_TYPE_CONFIG.items():
        subset = filter_liquid(chain, tt)
        calls = subset[subset["type"] == "call"].to_dict("records")
        puts = subset[subset["type"] == "put"].to_dict("records")
        result[tt] = {"calls": calls, "puts": puts}
    return result
