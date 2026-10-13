from unittest.mock import patch
import pytest

from src.engine.voting import Decision
from src.engine.risk_rules import evaluate


BASE_ACCOUNT = {
    "equity": 1000.0,
    "cash": 1000.0,
    "buying_power": 1000.0,
    "options_trading_level": 2,
}

GOOD_DECISION = Decision(
    action="BUY_CALL",
    trade_type="SHORT_SWING",
    confidence=75,
)


def _eval(decision=None, account=None, positions=None, today_trades=0, **kw):
    return evaluate(
        decision=decision or GOOD_DECISION,
        account=account or BASE_ACCOUNT,
        positions=positions or [],
        today_trades=today_trades,
        **kw,
    )


@patch("src.engine.risk_rules.is_market_open", return_value=True)
@patch("src.engine.risk_rules.is_within_n_min_of_close", return_value=False)
def test_approves_valid_trade(mock_close, mock_open):
    result = _eval()
    assert result.approved


@patch("src.engine.risk_rules.is_market_open", return_value=False)
def test_blocks_outside_market_hours(mock_open):
    result = _eval()
    assert not result.approved
    assert "trading window" in result.reason


@patch("src.engine.risk_rules.is_market_open", return_value=True)
@patch("src.engine.risk_rules.is_within_n_min_of_close", return_value=False)
def test_blocks_daily_cap(mock_close, mock_open):
    result = _eval(today_trades=2)
    assert not result.approved
    assert "cap" in result.reason


@patch("src.engine.risk_rules.is_market_open", return_value=True)
@patch("src.engine.risk_rules.is_within_n_min_of_close", return_value=False)
def test_blocks_low_equity(mock_close, mock_open):
    acct = {**BASE_ACCOUNT, "equity": 500.0}
    result = _eval(account=acct)
    assert not result.approved
    assert "floor" in result.reason


@patch("src.engine.risk_rules.is_market_open", return_value=True)
@patch("src.engine.risk_rules.is_within_n_min_of_close", return_value=False)
def test_blocks_daily_loss(mock_close, mock_open):
    result = _eval(today_realized_pnl_pct=-6.0)
    assert not result.approved
    assert "daily loss" in result.reason


@patch("src.engine.risk_rules.is_market_open", return_value=True)
@patch("src.engine.risk_rules.is_within_n_min_of_close", return_value=False)
def test_blocks_no_trade_decision(mock_close, mock_open):
    d = Decision(action="NO_TRADE", confidence=80)
    result = _eval(decision=d)
    assert not result.approved


@patch("src.engine.risk_rules.is_market_open", return_value=True)
@patch("src.engine.risk_rules.is_within_n_min_of_close", return_value=False)
def test_blocks_low_confidence(mock_close, mock_open):
    d = Decision(action="BUY_CALL", trade_type="SHORT_SWING", confidence=50)
    result = _eval(decision=d)
    assert not result.approved
    assert "confidence" in result.reason


@patch("src.engine.risk_rules.is_market_open", return_value=True)
@patch("src.engine.risk_rules.is_within_n_min_of_close", return_value=True)
def test_blocks_scalp_near_close(mock_close, mock_open):
    d = Decision(action="BUY_CALL", trade_type="SCALP", confidence=80)
    result = _eval(decision=d)
    assert not result.approved
    assert "SCALP" in result.reason


@patch("src.engine.risk_rules.is_market_open", return_value=True)
@patch("src.engine.risk_rules.is_within_n_min_of_close", return_value=False)
def test_blocks_contract_too_expensive(mock_close, mock_open):
    d = Decision(action="BUY_CALL", trade_type="SCALP", confidence=80)
    result = _eval(decision=d, contract_cost_usd=75.0)  # SCALP cap is $50
    assert not result.approved
    assert "cap" in result.reason


@patch("src.engine.risk_rules.is_market_open", return_value=True)
@patch("src.engine.risk_rules.is_within_n_min_of_close", return_value=False)
def test_blocks_fomc_imminent(mock_close, mock_open):
    result = _eval(is_fomc_imminent=True)
    assert not result.approved
    assert "FOMC" in result.reason
