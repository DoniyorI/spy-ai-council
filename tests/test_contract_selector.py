import pandas as pd
import pytest

from src.engine.contract_selector import select


def _make_chain():
    # mid prices kept low so mid*100 stays within per-type position caps:
    # SCALP cap=$50 → mid≤0.50, SHORT_SWING cap=$100 → mid≤1.00
    return pd.DataFrame([
        # Good SHORT_SWING call — mid=0.80 → $80 ≤ $100 cap ✓
        {"symbol": "SPY_GOOD_CALL", "type": "call", "strike": 512.0, "dte": 15,
         "bid": 0.75, "ask": 0.85, "mid": 0.80, "spread_pct": 9.0,
         "volume": 500, "open_interest": 1500, "delta": 0.44, "implied_volatility": 0.18},
        # Tight spread alternative — mid=0.70 → $70 ≤ $100 cap ✓
        {"symbol": "SPY_TIGHT_CALL", "type": "call", "strike": 514.0, "dte": 14,
         "bid": 0.65, "ask": 0.75, "mid": 0.70, "spread_pct": 5.0,
         "volume": 600, "open_interest": 2000, "delta": 0.40, "implied_volatility": 0.17},
        # CALL but spread too wide — filtered out
        {"symbol": "SPY_WIDE_CALL", "type": "call", "strike": 516.0, "dte": 18,
         "bid": 0.20, "ask": 0.60, "mid": 0.40, "spread_pct": 100.0,
         "volume": 100, "open_interest": 300, "delta": 0.35, "implied_volatility": 0.20},
        # PUT — mid=0.75 → $75 ≤ $100 cap ✓
        {"symbol": "SPY_GOOD_PUT", "type": "put", "strike": 508.0, "dte": 15,
         "bid": 0.70, "ask": 0.80, "mid": 0.75, "spread_pct": 9.5,
         "volume": 400, "open_interest": 1200, "delta": -0.40, "implied_volatility": 0.18},
        # SCALP call (DTE 3) — mid=0.40 → $40 ≤ $50 cap ✓
        {"symbol": "SPY_SCALP_CALL", "type": "call", "strike": 511.0, "dte": 3,
         "bid": 0.35, "ask": 0.45, "mid": 0.40, "spread_pct": 7.0,
         "volume": 700, "open_interest": 2500, "delta": 0.50, "implied_volatility": 0.22},
    ])


def test_select_short_swing_call():
    chain = _make_chain()
    result = select("BUY_CALL", chain, "SHORT_SWING")
    assert result is not None
    assert result["type"] == "call"
    assert 7 <= result["dte"] <= 21


def test_select_put():
    chain = _make_chain()
    result = select("BUY_PUT", chain, "SHORT_SWING")
    assert result is not None
    assert result["type"] == "put"


def test_select_scalp():
    chain = _make_chain()
    result = select("BUY_CALL", chain, "SCALP")
    assert result is not None
    assert result["dte"] <= 7
    assert result["symbol"] == "SPY_SCALP_CALL"


def test_prefers_ai_suggestion():
    chain = _make_chain()
    result = select("BUY_CALL", chain, "SHORT_SWING", ai_preferred="SPY_TIGHT_CALL")
    assert result is not None
    assert result["symbol"] == "SPY_TIGHT_CALL"


def test_ai_suggestion_not_in_set_falls_back():
    chain = _make_chain()
    # Wide spread contract should be filtered out
    result = select("BUY_CALL", chain, "SHORT_SWING", ai_preferred="SPY_WIDE_CALL")
    assert result is not None
    assert result["symbol"] != "SPY_WIDE_CALL"


def test_empty_chain_returns_none():
    chain = pd.DataFrame()
    result = select("BUY_CALL", chain, "SHORT_SWING")
    assert result is None


def test_no_matching_dte_returns_none():
    chain = _make_chain()
    # SWING needs 21-45 DTE — no contracts in chain have that
    result = select("BUY_CALL", chain, "SWING")
    assert result is None
