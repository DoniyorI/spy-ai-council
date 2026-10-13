from dataclasses import dataclass
from typing import Optional

from config.settings import (
    MAX_TRADES_PER_DAY,
    MIN_EQUITY_FLOOR,
    DAILY_LOSS_LIMIT_PCT,
    MIN_CONFIDENCE,
    TRADE_TYPE_CONFIG,
)
from src.engine.voting import Decision
from src.utils.market_hours import is_market_open, is_within_n_min_of_close
from src.utils.logging_config import log


@dataclass
class RiskResult:
    approved: bool
    reason: str


def _block(reason: str) -> RiskResult:
    log.info(f"Risk BLOCK: {reason}")
    return RiskResult(approved=False, reason=reason)


def _approve() -> RiskResult:
    return RiskResult(approved=True, reason="ok")


def evaluate(
    decision: Decision,
    account: dict,
    positions: list[dict],
    today_trades: int,
    today_realized_pnl_pct: float = 0.0,
    contract_cost_usd: Optional[float] = None,
    is_fomc_imminent: bool = False,
) -> RiskResult:
    if not is_market_open(buffer_min=5):
        return _block("market not in trading window")

    if account.get("options_trading_level", 0) < 2:
        return _block("options trading level < 2")

    if today_trades >= MAX_TRADES_PER_DAY:
        return _block(f"daily trade cap reached ({today_trades}/{MAX_TRADES_PER_DAY})")

    if account.get("equity", 0) < MIN_EQUITY_FLOOR:
        return _block(f"equity {account['equity']:.2f} below floor {MIN_EQUITY_FLOOR}")

    if today_realized_pnl_pct <= -DAILY_LOSS_LIMIT_PCT:
        return _block(f"daily loss limit hit ({today_realized_pnl_pct:.1f}%)")

    if decision.action == "NO_TRADE":
        return _block("council voted NO_TRADE")

    if decision.confidence < MIN_CONFIDENCE:
        return _block(f"confidence {decision.confidence} < {MIN_CONFIDENCE}")

    if not decision.trade_type or decision.trade_type not in TRADE_TYPE_CONFIG:
        return _block(f"invalid trade_type: {decision.trade_type}")

    # Check for same-direction open position
    direction = "call" if "CALL" in decision.action else "put"
    open_options = [p for p in positions if p.get("is_option")]
    for pos in open_options:
        sym = pos["symbol"].lower()
        if ("c" in sym and direction == "call") or ("p" in sym and direction == "put"):
            return _block(f"already have open {direction} position: {pos['symbol']}")

    cfg = TRADE_TYPE_CONFIG[decision.trade_type]

    if contract_cost_usd and contract_cost_usd > cfg["max_position_size_usd"]:
        return _block(
            f"contract cost ${contract_cost_usd:.2f} > {decision.trade_type} cap ${cfg['max_position_size_usd']}"
        )

    if decision.trade_type == "SCALP" and is_within_n_min_of_close(30):
        return _block("no new SCALP entries in last 30 min before close")

    if is_fomc_imminent:
        return _block("FOMC decision within 2 hours — blackout")

    import os
    if os.path.exists("KILL_SWITCH"):
        return _block("KILL_SWITCH file present")

    return _approve()
