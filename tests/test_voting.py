import pytest
from src.ai.output_schema import AnalystOutput, CommitteeOutput
from src.engine.voting import decide, tally, check_committee_veto


def _analyst(direction, trade_type="SHORT_SWING", confidence=75):
    return AnalystOutput(
        analyst="trend_momentum",
        model="test",
        direction=direction,
        trade_type=trade_type,
        confidence=confidence,
        data_quality_score=80,
    )


def _committee(action, trade_type="SHORT_SWING"):
    return CommitteeOutput(
        analyst="risk_committee",
        model="test",
        final_action=action,
        trade_type=trade_type,
        confidence=75,
    )


def test_call_majority():
    outputs = [_analyst("CALL")] * 6 + [_analyst("PUT")] * 3
    p4 = [_committee("BUY_CALL")] * 3
    d = decide(outputs, p4)
    assert d.action == "BUY_CALL"
    assert d.trade_type == "SHORT_SWING"


def test_put_majority():
    outputs = [_analyst("PUT")] * 5 + [_analyst("CALL")] * 4
    p4 = [_committee("BUY_PUT")] * 3
    d = decide(outputs, p4)
    assert d.action == "BUY_PUT"


def test_no_majority_returns_no_trade():
    outputs = [_analyst("CALL")] * 4 + [_analyst("PUT")] * 4 + [_analyst("NONE")]
    p4 = [_committee("BUY_CALL")] * 3
    d = decide(outputs, p4)
    assert d.action == "NO_TRADE"


def test_low_confidence_blocks():
    outputs = [_analyst("CALL", confidence=40)] * 6 + [_analyst("NONE")] * 3
    p4 = [_committee("BUY_CALL")] * 3
    d = decide(outputs, p4)
    assert d.action == "NO_TRADE"


def test_committee_veto():
    outputs = [_analyst("CALL")] * 6 + [_analyst("NONE")] * 3
    p4 = [_committee("NO_TRADE")] * 2 + [_committee("BUY_CALL")]
    d = decide(outputs, p4)
    assert d.action == "NO_TRADE"


def test_committee_type_override():
    outputs = [_analyst("CALL", trade_type="SCALP")] * 6 + [_analyst("NONE")] * 3
    p4 = [_committee("BUY_CALL", trade_type="SHORT_SWING")] * 3
    d = decide(outputs, p4)
    assert d.action == "BUY_CALL"
    assert d.trade_type == "SHORT_SWING"  # committee override


def test_tally():
    outputs = [_analyst("CALL")] * 5 + [_analyst("PUT")] * 3 + [_analyst("NONE")]
    counts = tally(outputs)
    assert counts["CALL"] == 5
    assert counts["PUT"] == 3
    assert counts["NONE"] == 1


def test_veto_detection():
    p4 = [_committee("NO_TRADE")] * 2 + [_committee("BUY_CALL")]
    vetoed, reason = check_committee_veto(p4)
    assert vetoed is True


def test_no_veto():
    p4 = [_committee("BUY_CALL")] * 2 + [_committee("NO_TRADE")]
    vetoed, _ = check_committee_veto(p4)
    assert vetoed is False
