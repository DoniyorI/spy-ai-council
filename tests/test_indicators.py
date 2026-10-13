import math
import pandas as pd
import pytest

from src.data.indicators import sma, rsi, macd, atr, bollinger_bands, vwap


@pytest.fixture
def price_series():
    # 50 points — enough for MACD(12,26,9) which needs 26+9=35 minimum
    return pd.Series(range(100, 150), dtype=float)


@pytest.fixture
def ohlcv_df():
    closes = list(range(100, 130))
    return pd.DataFrame({
        "open": [c - 0.5 for c in closes],
        "high": [c + 1.0 for c in closes],
        "low":  [c - 1.0 for c in closes],
        "close": closes,
        "volume": [1_000_000] * 30,
    })


def test_sma_basic(price_series):
    # series is 100..149; last 10 values are 140..149
    result = sma(price_series, 10)
    assert result == pytest.approx(sum(range(140, 150)) / 10, abs=0.01)


def test_sma_short_series():
    assert math.isnan(sma(pd.Series([1.0, 2.0]), 10))


def test_rsi_range(price_series):
    result = rsi(price_series)
    assert 0 <= result <= 100


def test_rsi_all_up():
    # Monotonically rising → RSI should be very high
    s = pd.Series(range(50, 80), dtype=float)
    assert rsi(s) > 90


def test_rsi_short_series():
    assert math.isnan(rsi(pd.Series([1.0, 2.0, 3.0]), n=14))


def test_macd_keys(price_series):
    result = macd(price_series)
    assert "macd" in result
    assert "signal" in result
    assert "histogram" in result


def test_macd_histogram_is_diff(price_series):
    result = macd(price_series)
    assert abs(result["histogram"] - (result["macd"] - result["signal"])) < 0.001


def test_atr_positive(ohlcv_df):
    result = atr(ohlcv_df)
    assert result > 0


def test_bollinger_bands_order(price_series):
    bb = bollinger_bands(price_series, n=20)
    assert bb["upper"] > bb["middle"] > bb["lower"]


def test_vwap(ohlcv_df):
    result = vwap(ohlcv_df)
    # For uniform volume, VWAP ≈ average of typical prices
    assert result > 0
